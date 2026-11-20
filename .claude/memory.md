# WILO Memory

## Goal
Will a stranger who finds Wilo on their own use it, come back, and pay? Measured with paid cold traffic (#162).
Earlier: does an AI *plan* make Thom's training better (#25, from 2026-10-05).

## Status (2026-11-20)
- hiwilo.com serves the landing page and the app. Signed-out visitors land on `landing.html`.
- The coach lives in the tracker's chat (`fe/chat.js` → `wilo/chat.py` on Render). Usage is recorded per request
  (#143); each user has a spend cap (`WILO_CHAT_SPEND_LIMIT`, default $5) and new accounts wait on an invite list
  (`WILO_CHAT_UIDS`).
- Workouts flow through Firestore as one doc per workout (#126): the coach plans → `users/{uid}/workouts` → the
  tracker logs into the same doc → the coach reads it back.
- The Claude connector (`https://wilo-connector.onrender.com/mcp`) still works; locally, Claude Code uses the
  `wilo` stdio server.
- Firestore free tier: 50k reads a day for the whole app (hit on 2026-11-19 by a polling admin viewer). Reads that
  load a user's whole history are #225.
- Postgres migration on hold (since 2026-10-06): stay on Firestore, but don't over-invest in Firestore-only
  infrastructure.

## Decisions
- No Qdrant, no admin agent. Firestore holds the data.
- Pages are plain HTML, not a PWA (no service worker).
- `wilo/coach.md` is the only place for coaching instructions; Thom writes it.
- The repo is public: no other users' data in git.
- Old RunPod/Qwen experiments (`prior-art/`) were deleted in #194; they're in git history (`git checkout c6bb0bb -- prior-art`).

## Structure
- `fe/landing.html`: landing page. `fe/index.html`: tracker. `fe/chat.js`: coach chat. `fe/auth.js`: Google sign-in.
- `fe/day.html`: the Day page (morning / day / night). `fe/week.html`: the calendar, appointments in
  `users/{uid}/events` (#168).
- `wilo/`: data, MCP server, connector sign-in, coach chat, `coach.md`.
- `firestore.rules`: security rules for the `wilo` database.
- `docs/`: current reference docs and `docs/sessions/` session logs.
