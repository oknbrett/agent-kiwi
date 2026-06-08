---
name: log-client-observation
description: Turn a raw client message or metric into a structured, durable memory entry. Use whenever new information about a client arrives that is worth remembering — preferences, recurring patterns, injuries, scheduling constraints, or progress.
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
