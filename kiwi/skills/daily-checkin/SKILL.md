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

## Reconcile the evidence
If the prompt includes an "Observations under review" block, compare each listed
observation against what actually happened today:

- **confirmed** — today's signals are a clear instance of the pattern (e.g. the
  observation says "goes quiet when work is busy" and today he skipped, citing
  work). Cite the observation's id.
- **contradicted** — today's signals are clear evidence *against* the pattern.
  Cite the id.
- Neither list is for hunches. If today says nothing about an observation,
  leave it out. An empty list is the common, correct answer.

## Remember something new (only if it will change a future decision)
If today revealed a genuinely new pattern, save it via `memory_note` — and give
`note_trigger`: the explicit condition under which the note applies ("client
mentions travel", "a deadline week"). A note without a trigger is not saved.
Most days there is nothing new; an empty string is the right call.

## Output format
Return exactly this JSON object and nothing else:

```json
{
  "message": "the check-in text",
  "memory_note": "one-line new pattern worth saving, or empty string",
  "note_trigger": "when the note applies — required if memory_note is set, else empty string",
  "confirmed": ["ids of observations today's evidence confirms"],
  "contradicted": ["ids of observations today's evidence contradicts"]
}
```
