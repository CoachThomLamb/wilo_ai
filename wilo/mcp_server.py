"""
WILO MCP server (local, stdio). Exposes wilo.data as tools so Claude can
read and write Thom's workouts in users/{uid}/assigned and completed.

Registered in Claude Code as `wilo`:
    claude mcp add wilo -s local -- /home/thom/wilo/.venv/bin/python -m wilo.mcp_server

Over HTTP (local test of the remote transport; localhost only):
    .venv/bin/python -m wilo.mcp_server --http [--port 8000]          → http://127.0.0.1:8000/mcp, no sign-in
    .venv/bin/python -m wilo.mcp_server --http --auth [--port 8000]   → with sign-in (OAuth + Firebase login, wilo/auth.py)

Same config and key as the script (config/wilo.json; GOOGLE_APPLICATION_CREDENTIALS overrides).
Workout and profile writes (assign_workout, update_workout, update_profile) are dry runs unless write=True.
Todo writes save immediately.
"""

import html
import os
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.mcpserver import MCPServer

from wilo import data as wilo_data

# Run as `python -m wilo.mcp_server`, this file is __main__; register it under its real name too, so wilo/chat.py's
# import gets this same module (one server, one CHAT_UID) instead of loading a second copy.
if __name__ == '__main__':
    sys.modules.setdefault('wilo.mcp_server', sys.modules[__name__])

HERE = Path(__file__).resolve().parent

# Coaching instructions live only in coach.md (served by coaching_method); this and the tool descriptions say
# what the tools do, not how to coach.
INSTRUCTIONS = "The user's WILO workout data. Call coaching_method first: it returns the coaching method (coach.md)."
AUTH = False  # set when serving with sign-in; then current_uid() comes only from the token
CHAT_UID = ContextVar('chat_uid', default=None)  # set by /chat (wilo/chat.py) after it verifies the Firebase ID token
_db = None


def db():
    global _db
    _db = _db or wilo_data.connect()
    return _db


def current_uid():
    """Whose data the tools act on. With sign-in, the signed-in user's token (never config). Without it (stdio,
    or local --http), the user in config/wilo.json. In the tracker's chat, the uid /chat verified.
    Never a tool argument: Claude doesn't choose whose data to read."""
    if uid := CHAT_UID.get():
        return uid
    if AUTH:
        token = get_access_token()
        if not token or not token.subject:
            raise PermissionError('not signed in')
        return token.subject
    return wilo_data.CONFIG['uid']


def coaching_method() -> dict[str, Any]:
    """The coaching method (coach.md): how to coach with these tools. Call it first."""
    return {'method': (HERE / 'coach.md').read_text()}


def get_profile() -> dict[str, Any]:
    """The user's coaching profile: preferences (what they like and don't), limitations (injuries, pain, what to
    avoid), plan (their current split, schedule, goals) and coach notes. A new user has none yet (exists=false)."""
    return wilo_data.profile(db(), current_uid())


def update_profile(preferences: str | None = None, limitations: str | None = None, plan: str | None = None,
                   notes: str | None = None, write: bool = False) -> dict[str, Any]:
    """Edit the user's coaching profile. Each section is free text; pass the full new text of the sections you
    change (read get_profile first and keep what's still true), '' to empty one; sections left out stay as they
    are. Returns the changes. Dry run unless write=True."""
    sections = {'preferences': preferences, 'limitations': limitations, 'plan': plan, 'notes': notes}
    edits = {k: v for k, v in sections.items() if v is not None}
    return wilo_data.update_profile(db(), current_uid(), edits, write, datetime.now(timezone.utc))


def workout_schema() -> dict[str, Any]:
    """The JSON Schema every workout must match (workout → exercises → sets). Read it before writing a workout."""
    return wilo_data.SCHEMA


def recent_completed(limit: int = 5) -> dict[str, Any]:
    """The user's most recent completed workouts, newest first, with every set (lbs, reps, done, custom).
    inProgress: true = still going: the tracker saves as you go, so its done sets are what's
    logged so far; Finish sets inProgress to false."""
    return {'workouts': wilo_data.recent(db(), current_uid(), 'completed', limit)}


def recent_assigned(limit: int = 5) -> dict[str, Any]:
    """Most recently assigned (planned) workouts, newest assignedFor first. The app loads the earliest one not yet completed."""
    return {'workouts': wilo_data.recent(db(), current_uid(), 'assigned', limit)}


def get_workout(collection: Literal['assigned', 'completed'], doc_id: str) -> dict[str, Any]:
    """One workout by its doc ID. Edit the result and pass it to update_workout to change it."""
    snap = wilo_data.collection(db(), current_uid(), collection).document(doc_id).get()
    return {'docId': snap.id, **snap.to_dict()} if snap.exists else {'ok': False, 'errors': ['not found']}


def exercise_history(name: str, limit: int = 5) -> dict[str, Any]:
    """Past sets for an exercise, newest first. Loose match on the name (case, spacing, punctuation,
    plurals, word order), so 'push up' finds 'Pushups'. For synonyms, check exercise_names first."""
    return {'history': wilo_data.history(db(), current_uid(), name, limit)}


def exercise_names() -> dict[str, Any]:
    """Every distinct exercise name the user has logged, with how often and when last done.
    Names are free text, so the same exercise can appear under several names."""
    return {'names': wilo_data.names(db(), current_uid())}


def assign_workout(workout: dict[str, Any], write: bool = False) -> dict[str, Any]:
    """Post a new workout to the user's assigned list. Fills id and assignedFor if missing (assignedFor = the date
    it's for, e.g. '2026-10-08'). Validates against workout_schema. Dry run unless write=True."""
    return wilo_data.assign(db(), current_uid(), workout, write, datetime.now(timezone.utc))


def update_workout(collection: Literal['assigned', 'completed'], doc_id: str, workout: dict[str, Any],
                   write: bool = False) -> dict[str, Any]:
    """Replace an existing workout with an edited version (e.g. rename an exercise). Returns the list of
    field changes. Refuses missing docs and id changes. Dry run unless write=True.
    Mid-workout change: update the same assigned workout with the new plan (planned sets, no done
    flags); when the user taps Load, the tracker keeps their logged sets and takes the rest from it."""
    return wilo_data.update(db(), current_uid(), collection, doc_id, workout, write)


def list_todos(include_done: bool = False) -> dict[str, Any]:
    """The user's todos, open ones first: dated by due (earliest first), then undated. Each has a docId."""
    return {'todos': wilo_data.todos(db(), current_uid(), include_done)}


def add_todo(text: str, due: str | None = None, notes: str | None = None) -> dict[str, Any]:
    """Add a todo. due is free text, a date or a date and time (e.g. '2026-10-12' or '2026-10-12 19:00'),
    so timed todos double as a light agenda. Saves immediately (no dry run)."""
    return wilo_data.add_todo(db(), current_uid(), text, datetime.now(timezone.utc), due, notes)


def update_todo(doc_id: str, text: str | None = None, done: bool | None = None, due: str | None = None,
                notes: str | None = None) -> dict[str, Any]:
    """Change a todo: check it off (done=True), reopen it, edit text, due or notes. Leave a field out to keep it;
    pass '' to clear due or notes. Saves immediately (no dry run)."""
    changes = {'text': text, 'done': done, 'due': due, 'notes': notes}
    return wilo_data.update_todo(db(), current_uid(), doc_id, changes, datetime.now(timezone.utc))


def delete_todo(doc_id: str) -> dict[str, Any]:
    """Delete a todo for good. Prefer done=True for finished ones; delete only what the user wants gone."""
    return wilo_data.delete_todo(db(), current_uid(), doc_id)


TOOLS = [coaching_method, get_profile, update_profile, workout_schema, recent_completed, recent_assigned, get_workout, exercise_history, exercise_names,
         assign_workout, update_workout, list_todos, add_todo, update_todo, delete_todo]


def make_server(provider=None, issuer=None):
    """The WILO MCP server, plus the tracker's /chat. With a provider: OAuth sign-in (SDK endpoints) plus our Firebase login page."""
    kwargs = {}
    if provider:
        from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
        from wilo.auth import SCOPE
        kwargs = {'auth_server_provider': provider, 'auth': AuthSettings(
            issuer_url=issuer, resource_server_url=f'{issuer}/mcp', validate_token_resource=True, required_scopes=[SCOPE],
            client_registration_options=ClientRegistrationOptions(enabled=True, valid_scopes=[SCOPE], default_scopes=[SCOPE]),
            revocation_options=RevocationOptions(enabled=True))}
    s = MCPServer('wilo', instructions=INSTRUCTIONS, **kwargs)
    for fn in TOOLS:
        s.add_tool(fn)
    if provider:
        add_login_routes(s, provider)
    from wilo.chat import add_chat_routes
    add_chat_routes(s)
    return s


def add_login_routes(s, provider):
    from starlette.responses import HTMLResponse, JSONResponse
    page = (HERE / 'login.html').read_text()

    @s.custom_route('/login', methods=['GET'])
    async def login(request):
        pending = request.query_params.get('request', '')
        host = re.fullmatch(r'[A-Za-z0-9_-]{20,}', pending) and provider.pending_redirect_host(pending)
        if not host:  # unknown/expired request: never echo it back into the page
            return HTMLResponse('<p>This sign-in link has expired. Start again from Claude.</p>', status_code=400)
        return HTMLResponse(page.replace('{{REDIRECT_HOST}}', html.escape(host)).replace('{{REQUEST}}', pending))

    @s.custom_route('/login/callback', methods=['POST'])
    async def login_callback(request):
        from firebase_admin import auth as firebase_auth
        try:
            body = await request.json()
            db()  # makes sure the Firebase app is initialised
            uid = firebase_auth.verify_id_token(body['idToken'])['uid']
            return JSONResponse({'redirect': provider.complete_login(body['request'], uid)})
        except Exception as err:  # bad token, expired request, malformed body
            return JSONResponse({'error': str(err)}, status_code=400)


server = make_server()


def main():
    global AUTH, server  # --auth switches the module-level server and current_uid() to sign-in mode
    import argparse
    p = argparse.ArgumentParser(description='WILO MCP server. Default: stdio (Claude Code launches it).')
    p.add_argument('--http', action='store_true', help='serve Streamable HTTP at http://127.0.0.1:PORT/mcp instead')
    p.add_argument('--port', type=int, default=int(os.environ.get('PORT', 8000)), help='default: $PORT (Cloud Run) or 8000')
    p.add_argument('--auth', action='store_true', help='with --http: require OAuth sign-in (Firebase Google login)')
    p.add_argument('--public-url', help='with --http --auth: public https:// address (e.g. on Cloud Run). '
                                        'Used as the OAuth issuer, and listens on all interfaces')
    args = p.parse_args()
    if args.auth and not args.http:
        p.error('--auth needs --http')
    if args.public_url is not None and not args.auth:
        p.error('--public-url needs --auth: the server is only ever exposed with sign-in on')
    if args.public_url is not None and not args.public_url.startswith('https://'):  # also catches an empty $PUBLIC_URL
        p.error('--public-url must be https://')
    if args.auth:
        from wilo.auth import Store, WiloAuthProvider
        AUTH = True
        # Locally: http://localhost (Firebase Auth allows localhost by default). Hosted: the public https:// address.
        issuer = args.public_url.rstrip('/') if args.public_url is not None else f'http://localhost:{args.port}'
        server = make_server(WiloAuthProvider(Store(db()), f'{issuer}/login', resource=f'{issuer}/mcp'), issuer)
    if args.http:
        # Public interfaces only behind sign-in (--public-url implies --auth); otherwise localhost only.
        host = '0.0.0.0' if args.public_url is not None else '127.0.0.1'
        server.run(transport='streamable-http', host=host, port=args.port)
    else:
        server.run()


if __name__ == '__main__':
    main()
