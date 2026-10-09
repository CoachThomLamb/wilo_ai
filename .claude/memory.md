# WILO Memory

## MVP Goal
Does an AI *plan*, delivered to the phone day by day, make training better? The loop: conversation → plan → calendar → workout → review → adjust (#25). Changed 2026-10-05: one workout at a time with no plan wasn't enough.

## Status (2026-10-09)
- Workouts flow through Firestore: Claude (via the `wilo` tools) → `users/{uid}/assigned` → `fe/index.html` → `users/{uid}/completed` → Claude.
- The Claude connector is live on Render (`https://wilo-connector.onrender.com/mcp`) and usable from the phone app. Locally, Claude Code uses the `wilo` stdio server.
- Thom's direction (#45): Wilo becomes the one place for the day (training + todos + events), coach on top.
- Postgres migration on hold (2026-10-06): stay on Firestore, but don't over-invest in Firestore-only infrastructure.

## Decisions
- No Qdrant, no admin agent. Firestore holds the workouts.
- The tracker is plain HTML, not a PWA (no service worker).
- `prior-art/`: old RunPod/Qwen experiments, kept for reference.

## Structure
- `fe/index.html`: tracker. `fe/builder.html`: program builder. `fe/auth.js`: Google sign-in.
- Coach: the `wilo-workout-coach` skill lives on claude.ai, not in this repo.
- `firestore.rules`: security rules for the `wilo` database.
- `docs/`: specs, planning docs, dev-ops notes, and `docs/sessions/` session logs.
