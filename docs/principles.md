# WILO principles

## Separation of concerns: config, code, data, instructions, LLM
Agreed 2026-10-03 (instructions added 2026-10-07). Every part of WILO belongs to one of five layers.

| Layer | Holds | In WILO today |
|---|---|---|
| **Config** | Settings that change per environment | `config/wilo.json`: project, database, uid, key path |
| **Code** | Every deterministic step, written once and tested | `scripts/wilo_data.py` (read, validate, write, update, history), `mcp/server.py` (the same functions as tools) |
| **Data** | The workouts, in one defined shape | Firestore `users/{uid}/assigned` and `completed`; `schema/workout.schema.json` |
| **Instructions** | Text written for the LLM: how to use WILO, what each tool does, coaching rules | Still mixed into code: the MCP server's `instructions=` and the 8 tool docstrings (sent to Claude as tool descriptions) in `mcp/server.py`; also the coach skill on claude.ai. To move into one file (#40) |
| **LLM** | Judgment only | Read history, talk with Thom, decide the next workout, spot synonyms, write the workout JSON |

What follows from it:
- **If code can do it, code does it.** The LLM never writes code at runtime, and never talks to Firestore directly. It calls fixed commands or tools.
- **The data shape is defined once,** in the schema file. Code validates against it, and the LLM reads it (the `workout_schema` tool) before writing a workout.
- **Instructions live apart from code,** the way the schema does for data: one place, editable without touching Python, read by the LLM. Code docstrings are for developers. (Not there yet: #40.)
- **The LLM's part stays thin:** "call this tool with this JSON." Instructions that describe the data by hand drift; that's what happened to the old `workout_reader.md`.
- **Judgment stays with the LLM and Thom:** which names mean the same exercise, what to change after a review, how hard to push. Code doesn't guess at these.
- **Code decides whose data:** the tools act on the signed-in user (`current_uid()`). It's never a tool argument, so the LLM can't choose whose workouts it reads or writes.
