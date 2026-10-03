# 2026-10-03: auth merged, coach design agreed

## Design principle: separation of concerns

| Layer | What it holds | WILO |
|---|---|---|
| **Config** | Settings that change per environment | Project ID, database name, collection names, credentials path |
| **Code** | Every deterministic step, written once and tested | Python: read, validate, write, update, generate IDs |
| **Data** | The workouts, in one defined shape | Firestore docs + a schema file in the repo |
| **LLM** | Judgment only | Read history, talk with Thom, decide the next workout, output JSON |

- If a script can do it, a script does it. The LLM never writes code at runtime.
- The data shape is defined once, in a schema file. The code validates against it, and the LLM reads it at the start of the task.
- The skill stays thin: "run this command, give it this JSON."

## What happened today
- Merged #13 (auth module + per-user rule) and #16 (optional sign-in in tracker and builder).
- Merged #17: root `CLAUDE.md`, plus `instructions.md` and `memory.md` updated to current state.
- Updated #15 step 3: Firestore reads and writes move into `scripts/wilo_data.py`, and the skill calls it.

## Found: coach and app are out of sync
- The coach (regular Claude chat + `wilo-workout-coach` skill + `wilo_fs.py`) reads `sessions` and writes `programs`, in the old nested shape.
- The app reads `assigned` and writes `completed`.
- So the coach hasn't seen workouts since Sept 30, and the workouts it posts don't load in the app.
- `wilo_fs.py` isn't in the repo.

## Open questions
- Where does `wilo_fs.py` live? Bring it into the repo as the starting point for `wilo_data.py`?
- Who or what writes to `assigned`? The Oct 1 workout got there somehow.
- `scripts/fetch_session.py` is outdated (reads `sessions`): delete it or update it?

## Next
- Build `scripts/wilo_data.py` + schema file + config (#15 step 3), then slim the coach skill down to calling it.
