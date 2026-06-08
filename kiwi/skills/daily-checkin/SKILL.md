---
name: daily-checkin
description: Compose a short, personal daily check-in message to a single client, grounded in their memory and recent observations. Use during the autonomous daily run when a client is due a touchpoint and nothing needs escalating.
---
# Daily Check-in

Write one short check-in message (2–4 sentences) to the client, as their coach's
assistant. The goal is to keep them engaged and surface anything useful for the
coach — not to coach them medically.

## Ground it in what you know
Read the client's memory block before writing. Reference something specific and
recent: a session they did, a goal milestone, a pattern you've observed. A
generic "how's training going?" is a failure — it signals you aren't paying
attention.

## Respect the client's patterns
- If memory says they **downplay problems**, ask a concrete question that makes a
  real issue easy to surface ("any aches or niggles this week, even small ones?").
- If memory says they **go quiet when busy**, keep it light and low-effort to
  reply to.
- If they are **close to a goal milestone**, acknowledge it.

## Tone
Warm, brief, human. No emoji. No exclamation-mark spam. You are an assistant the
client trusts, not a marketing bot.

## Output format
Return exactly this JSON object and nothing else:

```json
{
  "message": "the check-in text",
  "memory_note": "optional one-line note worth saving about this client, or empty string"
}
```
