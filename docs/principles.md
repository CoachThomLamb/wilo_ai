# WILO principles

## Separation of concerns: config, code, data, LLM
Agreed 2026-10-03. Every part of WILO belongs to one of four layers.

| Layer | Holds | In WILO today |
|---|---|---|
| **Config** | Settings that change per environment | `config/wilo.json`: project, database, uid, key path |
| **Code** | Every deterministic step, written once and tested | `scripts/wilo_data.py` (read, validate, write, update, history), `mcp/server.py` (the same functions as tools) |
| **Data** | The workouts, in one defined shape | Firestore `users/{uid}/assigned` and `completed`; `schema/workout.schema.json` |
| **LLM** | Judgment only | Read history, talk with Thom, decide the next workout, spot synonyms, write the workout JSON |

What follows from it:
- **If code can do it, code does it.** The LLM never writes code at runtime, and never talks to Firestore directly. It calls fixed commands or tools.
- **The data shape is defined once,** in the schema file. Code validates against it, and the LLM reads it (the `workout_schema` tool) before writing a workout.
- **The LLM's part stays thin:** "call this tool with this JSON." Instructions that describe the data by hand drift; that's what happened to the old `workout_reader.md`.
- **Judgment stays with the LLM and Thom:** which names mean the same exercise, what to change after a review, how hard to push. Code doesn't guess at these.
- **Code decides whose data:** the tools act on the signed-in user (`current_uid()`). It's never a tool argument, so the LLM can't choose whose workouts it reads or writes.
