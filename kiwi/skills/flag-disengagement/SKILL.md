---
name: flag-disengagement
description: Decide whether a client is at risk of disengaging or dropping out, and what to do about it. Use this whenever a client goes quiet, misses sessions, stops replying to check-ins, cancels repeatedly, or their adherence noticeably shifts — and equally to confirm that a single ordinary busy week is NOT treated as a dropout risk. This is the adherence-risk counterpart to flag-health-risk: that one routes physical risk to the coach, this one routes retention risk.
---
# Flag Disengagement

You are judging whether a client is drifting away — and, if so, whether to nudge
them yourself or pull the human coach in. Losing a client is usually slow and
quiet: a missed session, then a skipped reply, then nothing. Caught early, a
light touch brings them back; caught late, they're gone. Your job is to catch it
early without crying wolf over a normal off-week.

## Decision tiers

- **reengage** — send a low-friction nudge now. The client is slipping but a
  single warm, easy-to-answer message can plausibly turn it around.
- **monitor** — note the signal and watch for a pattern, but don't act yet.
- **escalate** — loop in the human coach. The drift is established or the reason
  may be something an assistant shouldn't handle alone (frustration with
  results, a life event, a complaint).

## Reengage when
- A **streak breaks**: a reliably-consistent client misses a session or skips a
  check-in for the first time in a while.
- They've gone **quiet for a few days** after being responsive, with no reason
  given.
- Memory says they **go quiet when work is busy** and the timing fits — a nudge
  that's easy to reply to respects the pattern.

## Escalate when
- **Repeated** misses or unanswered check-ins — a trend, not a blip.
- The client signals **frustration, doubt, or a life event** ("not sure this is
  working", "things are a lot right now"). That's a human conversation.
- A **cancellation or payment** signal, or anything that reads as "thinking about
  quitting".

## Do NOT flag (normal variance)
- A **single** planned skip the client already explained ("away this weekend").
- One ordinary busy week with no prior pattern of dropping off.
- A client who is **consistently engaged** and simply replied a little slower
  than usual.

## The tie-breaker rule
When genuinely uncertain between **reengage and monitor, choose reengage** — a
warm low-effort nudge costs the client almost nothing and a lost client costs a
lot. But the same restraint as health triage applies in reverse: nudging someone
who's perfectly engaged is noise that makes your nudges easy to ignore. Match the
response to the evidence.

## Output format
Return exactly this JSON object and nothing else:

```json
{
  "decision": "reengage | monitor | escalate",
  "reason": "one sentence: what made this that tier",
  "recommended_action": "the nudge to send, or what the coach should do — empty string if monitor"
}
```

## Worked examples
- Reliable client, first missed check-in in a month → `reengage` — "Streak
  broke; a single easy nudge likely brings them back." Action: "Send a short,
  low-pressure check-in that's easy to reply to."
- Memory: *"goes quiet when work is busy"*; quiet for three days mid-deadline →
  `reengage` — pattern fits, respect it with a light touch.
- Two missed sessions and two unanswered check-ins in one week → `escalate` —
  established drift; the coach should reach out personally.
- *"Honestly not sure this is working for me"* → `escalate` — doubt about results
  is a human conversation, not an assistant nudge.
- Client said *"away at a wedding this weekend"* and skipped Saturday → `monitor`
  (or nothing) — a planned, explained, one-off skip is not disengagement.
