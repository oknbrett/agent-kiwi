---
name: log-client-observation
description: Turn a raw client message or metric into a structured, durable memory entry — or decide it isn't worth saving. Use this whenever new information about a client arrives that might change a future decision: preferences, recurring patterns, injuries, scheduling constraints, or progress. Use it even when you suspect the answer is "don't save" — deciding what NOT to remember is half the job.
---
# Log Client Observation

Convert one raw signal into at most one durable memory entry. Most messages are
not worth saving — only persist things that will change how the coach or the
agent acts later.

## What is worth saving
- **Durable facts** → type `client_profile` (a stable goal, an injury history, a
  hard scheduling constraint). These never decay.
- **Patterns** → type `observation`. A pattern needs an explicit **trigger**: the
  condition under which it applies. "Skips Tuesday sessions" is not enough;
  "tends to skip mid-week sessions when work is busy" with trigger "a weekday
  session is scheduled during a busy work week" is.
- **Episodic state** → type `waiting_for_reply` or `checkin_sent` when relevant.

## What is NOT worth saving
- One-off small talk, transient mood, anything already captured.
- Restating the message verbatim. Distil the *signal*, not the text.

## Observation subtypes
Pick one: `training` (how they respond to load/programming), `recovery` (sleep,
soreness, rest patterns), `adherence` (whether and when they show up / reply).

## Output format
Return exactly this JSON object and nothing else. If nothing is worth saving,
return `{"save": false}`.

```json
{
  "save": true,
  "type": "client_profile | observation | waiting_for_reply | checkin_sent",
  "body": "the distilled fact or pattern",
  "subtype": "training | recovery | adherence (observations only, else omit)",
  "trigger": "explicit fire condition (observations only, else omit)"
}
```

## Worked examples
- *"I had ACL surgery on my left knee last year"* → durable fact.
  `{"save": true, "type": "client_profile", "body": "ACL reconstruction on left knee (last year); cleared for light loading only"}`
- *"I keep skipping Tuesdays when work piles up"* → a pattern; needs a trigger.
  `{"save": true, "type": "observation", "body": "Tends to skip mid-week sessions during busy work periods", "subtype": "adherence", "trigger": "a weekday session is scheduled during a busy work week"}`
- *"ugh today was rough, so tired"* → transient mood, no durable signal.
  `{"save": false}`
- *"my goal is really just to get back into a routine"* but the goal is already
  on file → already captured, don't duplicate. `{"save": false}`
