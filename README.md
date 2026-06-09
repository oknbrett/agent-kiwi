# Agent Kiwi

![agent eval](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/oknbrett/agent-kiwi/main/eval/badge.json)

An AI coach-assistant for a solo personal trainer. It triages what clients
report, sends grounded daily check-ins, and — the part that matters — **knows
when to pull the human coach in** and when to stay out of the way.

Kiwi is a portfolio project: a compact, end-to-end agent that shows the patterns
I use in production agent work — a real memory engine, Agent Skills with
progressive disclosure, and an outcome-graded eval suite — in a clean, sharable
domain. It is deliberately small enough to read in one sitting.

> **Why it's built this way:** see [`DESIGN_NOTES.md`](DESIGN_NOTES.md) for the
> decisions, the alternatives I rejected, and the trade-offs I accepted.

---

## What it demonstrates

**1. A real agent, not a prompt wrapper.** `kiwi/agent.py` runs a manual
tool-use loop: it loads its own instructions on demand, executes tools, feeds
results back, and loops until done. It keeps a structured, per-client memory that
it reads before acting and updates after.

**2. It knows when to involve a human.** The whole point of a coaching assistant
is routing risk to the human, not playing doctor. Kiwi triages every client
signal into `escalate` / `monitor` / `none`:

| Client | Says | Decision | Why |
|---|---|---|---|
| Sofia (post-ACL) | "sharp pain in my surgical knee, worse going downstairs" | **escalate** | New, localized, movement-provoked pain at a post-surgical site |
| Maya (marathon) | "legs are wrecked after the long run" | **none** | Textbook DOMS — a false alarm here trains the coach to ignore Kiwi |

The triage rule is asymmetric: **when genuinely uncertain between escalate and
monitor, escalate** — a false positive costs the coach a ten-second glance, a
false negative can cost a client an injury. But it does *not* inflate every ache,
because over-escalation is its own failure mode. Both directions are tested.

**3. It is tested like a non-deterministic system should be.** `python -m
eval.run` runs ~21 cases and gates on the result. The suite grades **outcome,
not path** — it asserts the escalation tier and the qualitative result, never the
exact tokens or which tools fired. It includes over-escalation negatives,
**context-isolation auto-fails** (seed one client's memory, run on another, fail
hard on any leak), and memory-fidelity checks. A monthly GitHub Actions cron
re-runs it and refreshes the badge above, so it reflects current behaviour rather
than a snapshot.

**4. Deliberate architecture.** Client = the isolation root (the analogue of a
tenant in a multi-tenant system). Skills, not sub-agents, carry the specialised
behaviour — see below.

---

## Architecture

```
                         ┌─────────────────────────────┐
   client message  ──►   │                             │
   app metric      ──►   │   KiwiAgent (agent.py)       │   ──►  client check-in
   (daily cron)    ──►   │   manual tool-use loop       │
                         │   + use_skill (disclosure)   │   ──►  coach digest
                         └──────────────┬──────────────┘        (escalations first)
                                        │
                          ┌─────────────┴─────────────┐
                          │  MemoryStore (memory.py)   │
                          │  one journal per client,   │
                          │  no cross-client read API  │
                          └────────────────────────────┘
```

Three channels share one loop: on-demand **client chat**, the autonomous
**daily run**, and the **coach digest** (recommendation-first — escalations
lead, routine "all fine" lines follow).

### The memory engine (`kiwi/memory.py`)

A framework-free port of a structured-memory engine I built in production:

- **Typed entries** — `client_profile` (never decays), `observation` (a learned
  pattern, must carry an explicit *trigger*), and episodic state.
- **Confidence dynamics** — observations carry a weight; confirmation raises it
  (+0.1), contradiction lowers it twice as fast (−0.2, asymmetric). Below a floor
  they stop surfacing. The daily run closes this loop: the model is shown the
  client's observations with ids and names which ones today's evidence confirmed
  or contradicted; `apply_evidence` moves the weights.
- **Deterministic compaction** — because entries are structured, pruning needs no
  LLM call: expire → provenance cascade (an observation whose sources are all
  gone fades) → age-prune → hard cap that protects profile facts.
- **Isolation by construction** — the only way to get memory into a prompt is
  `MemoryStore.context_for(client_id, today)`, which is single-client. There is
  no API to read across clients. `tests/test_memory_isolation.py` proves it.

The deterministic core is unit-tested with no model and no network
(`tests/` — 15 tests covering isolation, confidence, cascade, compaction, and
the agent loop via an injected fake client).

---

## Why Agent Skills, not sub-agents

Kiwi's specialised behaviours — triage, daily check-in, observation logging,
coach summary — live as **Agent Skills**: folders under `kiwi/skills/` each with
a `SKILL.md` (YAML frontmatter + instructions). They load by **progressive
disclosure**: only each skill's name + one-line description sit in context at
rest (Level 1); the full instructions are pulled in via the `use_skill` tool only
when a task triggers them (Level 2).

I chose skills over a constellation of sub-agents on purpose:

- **Context economy.** Twenty skills cost twenty short descriptions at rest, not
  twenty full instruction sets. The body tokens stay out of context until needed.
- **One reasoning thread.** A sub-agent swarm fragments state across agents and
  pays a serialization tax at every hand-off. Triage that needs the client's
  memory *and* the escalation rule shouldn't require two agents to negotiate —
  it's one decision with one context.
- **Legibility & versioning.** A skill is a flat Markdown file a domain expert
  (here, a coach) can read and edit. The escalation policy lives in
  `flag-health-risk/SKILL.md`, not buried in orchestration code.
- **Right tool for the shape of the problem.** Sub-agents earn their cost when
  you need genuine parallelism or hard context isolation between *tasks*. Kiwi's
  work is a single sequential judgement per signal — skills fit it better.

Isolation here is enforced at the **data** layer (per-client memory), which is
where it actually matters, not by spawning an agent per client.

---

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# deterministic core — no API key needed
pytest

# inspect the eval cases offline
python -m eval.run --list

# the live demo and eval need a key
export ANTHROPIC_API_KEY=sk-...
python simulate_week.py          # replay a scripted week → Friday's escalation
python -m eval.run --threshold 0.9
```

`simulate_week.py` replays four clients across a Monday–Friday week
(`data/clients.json`), building to Friday when Sofia reports sharp post-surgical
knee pain — Kiwi escalates it in the coach digest while correctly leaving Maya's
marathon DOMS alone.

---

## Layout

```
kiwi/
  domain.py        typed contracts (Client, Observation, Escalation, CoachDigest)
  memory.py        the structured memory engine + per-client MemoryStore
  agent.py         the agent loop (triage / daily_run / chat / summarize)
  coach.py         escalation collection + recommendation-first digest
  skill_loader.py  progressive disclosure (Level 1 catalog / Level 2 bodies)
  skills/          flag-health-risk, daily-checkin, log-client-observation,
                   summarize-for-coach  (each a SKILL.md)
eval/
  cases.jsonl      ~21 cases: escalation, over-escalation, isolation, fidelity
  judge.py         graders: deterministic decision, forbidden-token, LLM rubric
  run.py           one-command runner, scoreboard, gate, badge
tests/             deterministic unit tests (no network)
data/clients.json  the scripted demo week
simulate_week.py   the end-to-end demo
```

## Scope

Intentionally out of scope (kept simple on purpose): real messaging/calendar
integrations, a web UI, sub-agents, and a persistent database (the store
round-trips through plain JSON). The model is configurable in `kiwi/agent.py`.

Built by Khoi Nguyen Ong. MIT licensed.
