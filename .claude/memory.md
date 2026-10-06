# WILO Memory

## MVP Goal
Does an AI *plan*, delivered to the phone day by day, make training better? The loop: conversation → plan → calendar → workout → review → adjust (#25). Changed 2026-10-05: one workout at a time with no plan wasn't enough.

## Status (2026-10-05)
- Workouts flow through Firestore: coach agent → `assigned` → `fe/index.html` → `completed` → coach agent.
- Google sign-in merged (PRs #13, #16). Now: coaching loop design (#25), then #19 against it. #15 step 2 (data copy) alongside. Connector (#14) parked.
- Postgres migration planned, so don't over-invest in Firestore infrastructure.

## Decisions
- No Qdrant, no admin agent. Firestore holds the workouts.
- The tracker is plain HTML, not a PWA (no service worker).
- `prior-art/`: old RunPod/Qwen experiments, kept for reference.

## Structure
- `fe/index.html`: tracker. `fe/builder.html`: program builder. `fe/auth.js`: Google sign-in.
- Coach: the `wilo-workout-coach` skill lives on claude.ai, not in this repo.
- `firestore.rules`: security rules for the `wilo` database.
- `docs/`: specs, planning docs, dev-ops notes, and `docs/sessions/` session logs.
