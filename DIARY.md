# Engineering diary

A running log of the decisions behind Agent Kiwi — what I chose, and *why*. The
`DESIGN_NOTES.md` is the thematic argument; this is the timeline. Newest first.

---

## 2026-06-10 — Made the model calls survive production

**Decision.** Wrapped every model call in a retry layer (`kiwi/resilience.py`):
exponential backoff with jitter on transient faults, fail-fast on my own bugs,
and a structured JSON-lines trace of every attempt.

**Why.** A demo calls the model once and crashes on a hiccup. Production fails
for boring, transient reasons — the model is overloaded (HTTP 529), rate-limited
(429), or the connection blips — none of which mean "broken", only "try again in
a moment". The one line that matters is `is_retryable`: a 429 is worth waiting
out, but a 400 is *my* request being wrong, and retrying it just burns time and
money re-sending a broken call. So I retry only what waiting could fix, and let
real defects surface immediately.

**Trade-off.** I kept it minimal on purpose — no circuit breaker, no dead-letter
queue, trace goes to stderr not a real sink. Those are the next production steps,
and I'd rather name the boundary than pretend it isn't there. The whole layer is
dependency-free and unit-tested with an injected clock, so the backoff schedule
is asserted without ever actually waiting.

## 2026-06-09 — Grounded the eval judge in the full agent input

**Decision.** When the LLM-as-judge grades a "did the agent invent facts?" case,
it now sees everything the agent legitimately had: the client record *and* the
memory — not just the memory.

**Why.** The judge kept failing grounded outputs as "invented" because it
couldn't see the client's stated goal, which lives in the client record, not in
memory. A fidelity rubric is unjudgeable without the full ground truth. The fix
taught me the real definition of "grounding": it's *every* input the agent had,
not just the convenient subset.

## 2026-06 — Parse failures escalate, by policy

**Decision.** If triage returns something I can't parse into a verdict, the
agent escalates to the human — with a reason that says exactly that.

**Why.** The tempting default is "monitor" ("don't page the human over a
formatting bug"). That has the wrong failure mode: a real risk silently
downgraded because the model fenced its JSON wrong. My escalate-when-uncertain
rule has to apply to the *system's own* faults, not just the model's judgement
calls — an unreadable verdict is maximal uncertainty, and uncertainty routes to
the human. The reason string keeps it honest so it doesn't train the coach to
distrust real flags.

## 2026-06 — Mixed graders: deterministic where it's safety-critical

**Decision.** The eval uses three grading strategies, picked per case: exact
deterministic match on the escalation decision, a forbidden-token auto-fail for
context isolation, and an LLM-as-judge *only* for qualitative rubrics.

**Why.** I don't trust an LLM judge on the channel that matters most. The
safety-critical decision — escalate or not — is graded by exact outcome, no
model in the loop. Isolation leaks are a hard auto-fail, never a soft "the judge
thought it was fine". The judge earns its place only where there's genuinely no
single correct string. And every grader checks *outcome, not path*: the agent
can reason however it likes as long as the result is right.

## 2026-06 — A structured memory engine, not a vector store

**Decision.** Memory is a typed decision journal with confidence dynamics and
deterministic compaction — not embeddings over chat history.

**Why.** Different kinds of memory have different lifecycles: durable profile
facts should never decay, learned patterns should fade when contradicted, and
episodic state should age out. A flat similarity store flattens that distinction
away. Because the entries are *structured*, compaction needs no model call — it's
cheap, reproducible, and unit-testable. The confidence asymmetry (contradiction
costs twice what confirmation earns) is deliberate: being wrong should cost more
than being right earns, so stale beliefs fade fast.

## 2026-06 — Skills, not sub-agents

**Decision.** The specialised behaviours live as Agent Skills loaded by
progressive disclosure, not as a constellation of sub-agents.

**Why.** Triage needs the client's memory *and* the escalation policy at once —
that's one decision in one context, not a negotiation between two agents paying a
serialization tax at every hand-off. Skills also keep the cost flat as the
library grows: twenty skills cost twenty short descriptions at rest, not twenty
full instruction sets. Sub-agents earn their cost with real parallelism or hard
task isolation; Kiwi's work is one sequential judgement per signal, so they'd be
complexity I'd be paying for and not using.

## 2026-06 — Port the patterns into a clean public domain

**Decision.** Rather than publish a slice of the private production agent, I
rebuilt its engineering patterns — structured memory, human-in-the-loop
escalation, multi-tenant isolation, LLM-as-judge eval — in a small, readable
coaching domain anyone can open and judge in a sitting.

**Why.** A partial dump of a private multi-tenant codebase is *harder* to read
than a purpose-built project, and publishing it isn't mine alone to decide. The
real insight: I'm porting patterns I already authored, not inventing them cold —
lower-risk and faster than it feels, and it produces something clean and public.
The trade-off I accepted is that the domain is "toy"; I counter that by making
the *engineering* unmistakably real.
