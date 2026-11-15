# 2026-11-15: appointments and the Week page (#168)

## Why
Thom is tired of Apple and Google Calendar and wants Wilo to be the single source of truth for his
appointments, on his phone. Just for him ("I'm the CEO, things that help me are good"). He does **not**
want reminders. This is the first built piece of #45 (events), started while WILO is otherwise parked
for the job hunt.

## Decisions
- **Own collection, not the day doc:** `users/{uid}/events`, one doc per appointment
  (`date`, optional `time`, `text`, optional `notes`). The Day page saves its whole doc as you type, so
  events inside it would be overwritten by a stale page.
- **Kept out on purpose:** repeating events, end times, reminders, import from Google / Apple. Add them
  when real use asks.
- **No coach.md change.** The four event tools only describe what they do. If the coach should use the
  calendar when it plans workouts (the "smallest step" in #45), that line is Thom's to write in coach.md.
- **No rules change:** the per-user catch-all rule already covers `events`.

## Where it stopped
- Branch `feat/events-week`, pushed, no PR yet.
- Tested with the Python and node tests, and the pages rendered in headless Chromium against an
  in-memory stub. **Not yet tried against real Firestore or on the phone.**
- Not deployed: Hosting (the pages) and Render (the connector's new tools) both deploy from `main`.

## Next
1. Thom OKs a PR; merge; check Hosting and Render went live.
2. Thom adds a real appointment on his phone and from the Claude app.
3. Then decide from use: repeating events (weekly meetings) are the likely first ask.

## Noticed, not fixed
- The Day page's "Day" tab shows an empty pinned box when there are no strive / watch / wilos lines.
- The Day page's › stops at today, so future days are only reachable from the Week page.
