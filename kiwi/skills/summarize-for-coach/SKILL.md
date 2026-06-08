---
name: summarize-for-coach
description: Write the recommendation-first one-line summary of a single client for the coach's end-of-day digest. Use when assembling the coach digest after the daily run.
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
