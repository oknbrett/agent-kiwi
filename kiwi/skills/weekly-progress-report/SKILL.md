---
name: weekly-progress-report
description: Write a short, grounded weekly progress note about one client for the coach, reading across the week's memory rather than a single day. Use this when the coach wants a step back from the daily one-liner — a weekly review, a "how is X doing lately?", or prep before a session. The daily summarize-for-coach skill answers "what needs attention today?"; this one answers "what's the trend?".
---
# Weekly Progress Report

Step back from the day and tell the coach how this client's week actually went.
The coach uses this to prepare — for a session, a call, a decision about
programming — so it should read like a trusted assistant's honest brief, not a
cheerful recap.

## Read across the week, not the moment
The daily digest answers "what needs me today?". This answers "what's the
*trend*?". Look across the client's memory: which observations were confirmed or
contradicted, what escalations happened, whether adherence held or slipped,
whether they're moving toward their goal. A single day is a data point; a week is
a direction.

## Be honest, and stay grounded
- Lead with the **honest headline** — "Strong, consistent week" or "Drifting,
  worth a personal check-in" — not a default positive.
- Every point must come from the client record or memory. **Do not invent
  numbers, session counts, weights, times, or progress that aren't there.**
  Noting that a client has gone quiet, or restating their stated goal, is
  grounded; inventing a metric is a failure. If the week is thin on signal, say
  so plainly rather than padding it.
- End with **one** recommended focus for the coach — the single most useful thing
  to do next, not a list.

## Output format
Return exactly this JSON object and nothing else:

```json
{
  "headline": "the honest one-line read on the week",
  "observations": ["a grounded point from memory", "another, if there is one"],
  "recommended_focus": "the single most useful next action for the coach"
}
```

## Worked examples
**Example 1 — strong week**
Memory: hit a 30k long run, confirmed "responds well to higher mileage",
adherence solid.
Output:
```json
{
  "headline": "Strong, consistent week — peak mileage handled well.",
  "observations": [
    "Completed a 30k long run and reported feeling strong.",
    "The pattern that she responds well to higher mileage held up again this week."
  ],
  "recommended_focus": "Hold the current build; she's absorbing the load, so don't add volume yet."
}
```

**Example 2 — thin signal, be honest**
Memory: one logged session, no replies to two check-ins, no other detail.
Output:
```json
{
  "headline": "Quiet week — not enough signal, and that itself is the signal.",
  "observations": [
    "Only one session logged and two check-ins went unanswered.",
    "Nothing in memory explains the drop-off."
  ],
  "recommended_focus": "A short personal message from the coach to re-establish contact before it becomes a pattern."
}
```
