# WILO Memory

## MVP Goal
Does an AI-generated workout improve the gym session? Nothing else matters yet.

## Status (2026-10-03)
- Workouts flow through Firestore: coach agent → `assigned` → `fe/index.html` → `completed` → coach agent.
- Google sign-in merged (PRs #13, #16). Now: per-user data (#15 steps 2–4). Next: the Claude connector (#14), parked until #15 is done.
- Postgres migration planned, so don't over-invest in Firestore infrastructure.

## Decisions
- No Qdrant, no admin agent. Firestore holds the workouts.
- The tracker is plain HTML, not a PWA (no service worker).
- `prior-art/`: old RunPod/Qwen experiments, kept for reference.

## Structure
- `fe/index.html`: tracker. `fe/builder.html`: program builder. `fe/auth.js`: Google sign-in.
- Coach: the `wilo-workout-coach` skill lives on claude.ai, not in this repo. `scripts/fetch_session.py` and `coach_ai/skills/workout_reader.md` are outdated (old `sessions` / `programs` shape).
- `firestore.rules`: security rules for the `wilo` database.
- `docs/`: specs, planning docs, dev-ops notes, and `docs/sessions/` session logs.
