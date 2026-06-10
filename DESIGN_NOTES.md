# Design notes

Why Agent Kiwi is built the way it is. This is the "why this, not that" companion
to the README — the decisions, the alternatives I rejected, and the trade-offs I
accepted. It's a portfolio project, so the reasoning matters as much as the code.

## Why this domain

Kiwi is an assistant for a solo personal trainer. The domain is deliberately
mundane: it gives every interesting agent problem a concrete, legible shape —
a clear human-in-the-loop (the coach), a natural isolation boundary (the client),
and a safety-critical decision (is this a health risk?) that a non-engineer can
sanity-check. The point of the project isn't fitness; it's to show the
engineering patterns of a production agent in something anyone can read in a
sitting.

## Why a real agent loop, not a prompt wrapper

`agent.py` runs a manual tool-use loop: call the model, execute any tool calls,
feed results back, repeat until `end_turn`. I kept the loop hand-written rather
than reaching for a framework because:

- **The loop is the interesting part.** Hiding it behind a framework abstraction
  would defeat the purpose of a portfolio piece — you couldn't see the control
  flow, the stop conditions, or how tool results re-enter context.
- **Testability.** The loop takes an injected client, so the whole thing runs
  against a scripted fake model in `tests/test_agent_loop.py` — no network, no
  key. The non-deterministic core (the model) is isolated; the *machinery* around
  it is tested like ordinary code.

## Why Agent Skills, not sub-agents

The specialised behaviours — triage, disengagement-spotting, daily check-in,
client replies, observation logging, the daily digest, the weekly report — are
**skills** (a `SKILL.md` per folder), loaded by progressive disclosure: only
names + one-line descriptions sit in context at rest; full instructions load via
the `use_skill` tool when a task triggers them. Some are pinned to a structured
channel (triage forces `flag-health-risk`); the rest the model selects in the
open chat channel. Adding the last three skills cost the resting context only
three more one-line descriptions — which is the entire point.

I considered a sub-agent per behaviour and rejected it:

- **Context economy.** N skills cost N short descriptions at rest, not N full
  instruction sets. Body tokens stay out of context until needed.
- **One reasoning thread.** Triage needs the client's memory *and* the escalation
  policy at once — that's a single decision in a single context, not a
  negotiation between two agents with a serialization tax at the hand-off.
- **Legibility & versioning.** A skill is a flat Markdown file a domain expert
  (the coach) could read and edit. The escalation policy lives in
  `flag-health-risk/SKILL.md`, not buried in orchestration code.
- **Right tool for the shape.** Sub-agents earn their cost with genuine
  parallelism or hard task isolation. Kiwi's work is one sequential judgement per
  signal. Skills fit it; sub-agents would be cargo-culting complexity.

Isolation that actually matters here is enforced at the **data** layer (see
below), not by spawning an agent per client.

## Why a structured memory engine (and not a vector store)

`memory.py` is a typed decision journal, not embeddings-over-chat-history:

- **Typed entries** — `client_profile` (durable facts, never decay) vs
  `observation` (learned patterns that must carry an explicit *trigger*) vs
  episodic state. Different kinds of memory have different lifecycles; a flat
  similarity store flattens that distinction away.
- **Confidence dynamics** — observations carry a weight; confirmation nudges it
  up (+0.1), contradiction pulls it down twice as fast (−0.2). The asymmetry is
  deliberate: being wrong should cost more than being right earns, so stale
  beliefs fade quickly. Below a floor they stop surfacing.
- **Deterministic compaction** — because entries are *structured*, pruning needs
  no LLM call: expire → provenance cascade (an observation whose sources are all
  gone can no longer be re-confirmed, so it fades) → age-prune → a hard cap that
  protects profile facts. No model, so it's cheap, reproducible, and unit-testable.
- **Provenance cascade ordering** — the cascade runs against the live set
  *before* the age-prune, so an orphaned observation fades on the *next* pass, not
  the same one. That makes repeated runs idempotent — important when a cron fires
  it daily. `tests/test_memory_confidence.py` pins this exact behaviour.

## Why isolation lives at the data layer

The client is the isolation root — the analogue of a tenant in a multi-tenant
system. The only way to get memory into a prompt is
`MemoryStore.context_for(client_id, today)`, which is single-client by
construction. **There is no API to read across clients.** This mirrors row-level
security: the caller can only ever see its own tenant's rows.
`tests/test_memory_isolation.py` proves a leak is impossible even after many
writes — and the eval suite treats any cross-client leak as an automatic failure.

## Why the escalation rule is asymmetric

The triage skill biases toward escalation *when genuinely uncertain* between
escalate and monitor, because the stakes are asymmetric: a false positive costs
the coach a ten-second glance; a false negative can cost a client an injury.

But that bias is bounded. Over-escalation is its own failure mode — cry wolf and
the coach learns to ignore you, which is *worse* than not flagging. So clear DOMS
(sore legs after a hard run) must resolve to `none`, and the eval suite tests
both directions: escalation positives *and* over-escalation negatives. Safety and
restraint are graded together.

## Why a parse failure escalates

If triage returns something that can't be parsed into a verdict, Kiwi escalates
— with a reason that says so explicitly ("escalating by policy, not by
judgement"). The alternative, defaulting to `monitor`, reads safer ("don't page
the human over a formatting bug") but has the wrong failure mode: a real risk
silently downgraded because the model fenced its JSON wrong. The asymmetric
rule applies to the system's own faults, not just the model's judgement calls —
an unreadable verdict is maximal uncertainty, and uncertainty routes to the
human. The reason string keeps it honest: the coach can see it's a system
fault, not a health call, so it doesn't train them to distrust real flags.

## Why the model calls retry themselves, and leave a trace

A demo calls the model once and hopes. In production that call fails for boring,
*transient* reasons — the model is overloaded (HTTP 529), you hit a rate limit
(429), a connection blips. None of those mean the agent is broken; they mean
"try again in a moment". So every model call in `agent.py` goes through
`resilience.call_with_retry`, which retries transient faults with **exponential
backoff + jitter** and gives up loudly on the rest.

Two decisions worth calling out:

- **Retry only what might succeed on a retry.** A 429 or 529 is worth waiting
  out; a 400 (bad request) is *our* bug and re-sending it just burns time and
  money on the same broken call. `is_retryable` draws that line, so a real
  defect surfaces immediately instead of hiding behind four slow retries.
- **Backoff with jitter, not a tight loop.** Each wait doubles (0.5s, 1s, 2s…)
  and is capped, with a little randomness added so a fleet of agents recovering
  from the same outage don't all retry in lockstep and re-spike the service.

Alongside it, every call emits a structured **JSON-lines trace** (`CallTrace`):
channel, client, attempt, latency, retries, stop reason, token usage. When an
agent does something surprising in production, "we'll look into it" becomes
"here is exactly what it saw and decided at 14:32". `simulate_week.py --trace`
turns it on. The whole layer is dependency-free and unit-tested with an injected
`sleep`/`rng` (`tests/test_resilience.py`), so the retry schedule is asserted
deterministically with no real waiting and no network.

## Why the eval is built this way

A non-deterministic system still has to be tested like an engineered one.
`python -m eval.run` runs ~21 cases and gates on the result:

- **Outcome, not path.** It asserts the escalation *tier* and the qualitative
  result, never the exact tokens or which tools fired. The agent is free to reason
  however it likes as long as the outcome is right.
- **Mixed graders.** Safety-critical decisions are graded *deterministically*
  (decision == expected) — no LLM ambiguity in the channel that matters most.
  Context-isolation is a deterministic *auto-fail* (forbidden-token check).
  Only the qualitative channels (check-in quality, summaries, memory fidelity)
  use an LLM-as-judge, and even then it grades outcome against a rubric.
- **Scheduled, not one-shot.** An LLM agent drifts as models and prompts change.
  A monthly GitHub Actions cron re-runs the suite and refreshes the status badge,
  so the badge reflects *current* behaviour, not a snapshot from the day it was
  written.

## Accepted trade-offs / out of scope

Kept deliberately simple so the core ideas stay legible:

- **No real integrations** (messaging, calendar) — observations are seeded.
- **No database** — the store round-trips through plain JSON; persistence is a
  solved problem and not what this project is demonstrating.
- **Resilience is real but minimal** — model calls retry transient faults with
  backoff and emit a trace (see above). What's deliberately *not* here: a
  circuit breaker, a dead-letter queue for calls that exhaust their retries, and
  shipping the trace to a real sink (OpenTelemetry / a log aggregator) rather
  than stderr. Those are the next production steps, called out so the boundary
  is honest rather than implied.
- **UI is a visualisation, not a control plane** — the demo is a terminal
  replay (`simulate_week.py`); `dashboard/` renders the same scripted week for
  a coach's-eye view but does not drive the live agent. Wiring a UI to the
  loop is plumbing, not the patterns this project demonstrates.
- **No sub-agents** — see above; they'd add cost without buying anything here.

The model is a single constant in `agent.py`, swappable in one place.
