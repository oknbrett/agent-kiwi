---
name: summarize-for-coach
description: Write the recommendation-first one-line summary of a single client for the coach's end-of-day digest. Use this whenever assembling the daily coach digest, or any time the coach needs a single-glance "what about this client today?" line. This answers "what needs me today?" — for a week-level trend, use weekly-progress-report instead.
---
# Summarize for Coach

Write a single line about one client for the coach's daily digest. The coach
scans this in seconds across all their clients, so density and a clear
recommendation matter more than completeness.

## Lead with the recommendation
If there is an action the coach should take, put it first. "Check in with Tom —
two missed sessions this week" beats "Tom had a quiet week and missed a couple
of sessions, you might want to reach out."

## Rules
- One line. No preamble ("Here is a summary of...").
- State the **fact** and the **recommended action** (if any).
- If the client is on track and needs nothing, say so briefly — the coach values
  knowing who they can ignore today.
- Never invent metrics or progress that aren't in the memory/observations.

## Output format
Return exactly this JSON object and nothing else:

```json
{
  "summary": "the one-line summary, recommendation first"
}
```

## Worked examples
- Memory shows an escalation today (Sofia, surgical-knee pain) →
  *"Check in with Sofia today — she reported sharp surgical-knee pain; I've
  flagged it."* (Action first, the fact second.)
- Memory shows two missed sessions (Tom) →
  *"Reach out to Tom — two missed sessions this week, no reason given."*
- Client on track, nothing needed (Maya) →
  *"Maya's fine — strong week, no action needed."* (Telling the coach who they
  can ignore is itself useful.)
- Thin memory, no progress logged → *"Quiet day for Liam; nothing new to act
  on."* Never invent a metric to fill the line.
