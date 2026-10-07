"""
WILO MCP server (local, stdio). Exposes wilo.data as tools so Claude can
read and write Thom's workouts in users/{uid}/assigned and completed.

Registered in Claude Code as `wilo`:
    claude mcp add wilo -s local -- /home/thom/wilo/.venv/bin/python -m wilo.mcp_server

Same config and key as the script (config/wilo.json; GOOGLE_APPLICATION_CREDENTIALS overrides).
Writes (assign_workout, update_workout) are dry runs unless write=True.
"""

from datetime import datetime, timezone
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer

from wilo import data as wilo_data

server = MCPServer(
    'wilo',
    instructions=(
        "Thom's workout data. Read history before planning. Exercise names are free text: use "
        "exercise_names to spot synonyms. Always dry-run assign_workout/update_workout, show Thom the "
        "result, and only call again with write=True once he approves."
    ),
)
_db = None


def db():
    global _db
    _db = _db or wilo_data.connect()
    return _db


@server.tool()
def workout_schema() -> dict[str, Any]:
    """The JSON Schema every workout must match (workout → exercises → sets). Read it before writing a workout."""
    return wilo_data.SCHEMA


@server.tool()
def recent_completed(limit: int = 5) -> dict[str, Any]:
    """Thom's most recent completed workouts, newest first, with every set (lbs, reps, done, custom)."""
    return {'workouts': wilo_data.recent(db(), 'completed', limit)}


@server.tool()
def recent_assigned(limit: int = 5) -> dict[str, Any]:
    """Most recently assigned (planned) workouts, newest assignedFor first. The newest is what the app loads."""
    return {'workouts': wilo_data.recent(db(), 'assigned', limit)}


@server.tool()
def get_workout(collection: Literal['assigned', 'completed'], doc_id: str) -> dict[str, Any]:
    """One workout by its doc ID. Edit the result and pass it to update_workout to change it."""
    snap = wilo_data.collection(db(), collection).document(doc_id).get()
    return {'docId': snap.id, **snap.to_dict()} if snap.exists else {'ok': False, 'errors': ['not found']}


@server.tool()
def exercise_history(name: str, limit: int = 5) -> dict[str, Any]:
    """Past sets for an exercise, newest first. Loose match on the name (case, spacing, punctuation,
    plurals, word order), so 'push up' finds 'Pushups'. For synonyms, check exercise_names first."""
    return {'history': wilo_data.history(db(), name, limit)}


@server.tool()
def exercise_names() -> dict[str, Any]:
    """Every distinct exercise name Thom has logged, with how often and when last done.
    Names are free text: decide which ones mean the same exercise, and ask Thom when unsure."""
    return {'names': wilo_data.names(db())}


@server.tool()
def assign_workout(workout: dict[str, Any], write: bool = False) -> dict[str, Any]:
    """Post a new workout to Thom's assigned list. Fills id and assignedFor if missing (assignedFor = the date
    it's for, e.g. '2026-10-08'). Validates against workout_schema. Dry run unless write=True."""
    return wilo_data.assign(db(), workout, write, datetime.now(timezone.utc))


@server.tool()
def update_workout(collection: Literal['assigned', 'completed'], doc_id: str, workout: dict[str, Any],
                   write: bool = False) -> dict[str, Any]:
    """Replace an existing workout with an edited version (e.g. rename an exercise). Returns the list of
    field changes. Refuses missing docs and id changes. Dry run unless write=True."""
    return wilo_data.update(db(), collection, doc_id, workout, write)


def main():
    server.run()


if __name__ == '__main__':
    main()
