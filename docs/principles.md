# WILO principles

## Your job
- Keep Thom on the MVP path (`.claude/instructions.md`). He gets impulsive and goes down rabbit holes.
- When he wants to add something, ask: "does this help us get to the gym with a working app?" If no, park it.
- When something is good enough, say so and move on. Perfect is the enemy of done.
- Clean as you go: close or fold stale issues, delete merged branches, and fix stale docs as you notice them.
- Be a partner, not an order-taker. If something is a bad idea, say so and explain why.
- Tell him what you're doing and why before asking him to do anything. He's an active participant, not along for the ride.

## Separation of concerns: config, code, data, instructions, LLM
Agreed 2026-10-03 (instructions added 2026-10-07). Every part of WILO belongs to one of five layers.

| Layer | Holds | In WILO today |
|---|---|---|
| **Config** | Settings that change per environment | `config/wilo.json`: project, database, uid, key path |
| **Code** | Every deterministic step, written once and tested. GitHub is the source of truth | `wilo/data.py` (read, validate, write, update, history), `wilo/mcp_server.py` (the same functions as tools) |
| **Data** | The workouts, in one defined shape | Firestore `users/{uid}/assigned` and `completed`; `schema/workout.schema.json` |
| **Instructions** | Text written for the LLM: how to use WILO, what each tool does, coaching rules | `wilo/coach.md` (coaching method, #40); the server `INSTRUCTIONS` and tool docstrings in `wilo/mcp_server.py`; skills in `.claude/skills/wilo/` |
| **LLM** | Judgment only | Read history, talk with Thom, decide the next workout, spot synonyms, write the workout JSON |

What follows from it:
- **Everything has one home.** Each thing lives in exactly one place unless Thom says otherwise. One place makes errors easy to trace and setups easy to reproduce for other users. `.claude/instructions.md` maps where things live; it points, it doesn't copy.
- **If code can do it, code does it.** The LLM never writes code at runtime, and never talks to Firestore directly. It calls fixed commands or tools.
- **One path to the data: the wilo connector,** the same way a user reaches it (#87). Not the local stdio server, a Firebase skill, or an ad-hoc `firebase_admin` script.
- **The data shape is defined once,** in the schema file. Code validates against it, and the LLM reads it (the `workout_schema` tool) before writing a workout.
- **Instructions live apart from code,** the way the schema does for data: one place, editable without touching Python, read by the LLM. Code docstrings are for developers.
- **The LLM's part stays thin:** "call this tool with this JSON." Instructions that describe the data by hand drift; that's what happened to the old `workout_reader.md`.
- **Judgment stays with the LLM and Thom:** which names mean the same exercise, what to change after a review, how hard to push. Code doesn't guess at these.
- **Code decides whose data:** the tools act on the signed-in user (`current_uid()`). It's never a tool argument, so the LLM can't choose whose workouts it reads or writes.

## Decisions
- **Firestore holds the workouts.** No Qdrant, no admin agent.
- **Postgres migration on hold** (2026-10-06): stay on Firestore, but keep the app design DB-agnostic and don't over-invest in Firestore-only infrastructure.

## Understand the problem first
- **Before building, know the problem we're actually solving.** Restate the objective in your own words and get Thom's confirmation before writing code or filing work. If the restatement and the ask differ, stop and clear it up. Example: #87 was first written as "revoke prod access"; the real goal was "one path to the data, like a user".

## Keep it clean
- **Cruft is the biggest cost.** Leftover code, docs and other LLM output pile up cognitive load for the humans. End every session by cleaning up and cutting complexity.

## Changing this list
- When a new principle comes up during work, ask Thom before adding it. Then review the whole list for contradictions or regressions.
