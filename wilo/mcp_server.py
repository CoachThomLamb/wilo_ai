"""
WILO MCP server (local, stdio). Exposes wilo.data as tools so Claude can
read and write Thom's workouts in users/{uid}/assigned and completed.

Registered in Claude Code as `wilo`:
    claude mcp add wilo -s local -- /home/thom/wilo/.venv/bin/python -m wilo.mcp_server

Over HTTP (local test of the remote transport; localhost only):
    .venv/bin/python -m wilo.mcp_server --http [--port 8000]          → http://127.0.0.1:8000/mcp, no sign-in
    .venv/bin/python -m wilo.mcp_server --http --auth [--port 8000]   → with sign-in (OAuth + Firebase login, wilo/auth.py)

Same config and key as the script (config/wilo.json; GOOGLE_APPLICATION_CREDENTIALS overrides).
Writes (assign_workout, update_workout) are dry runs unless write=True.
"""

import html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.mcpserver import MCPServer

from wilo import data as wilo_data

HERE = Path(__file__).resolve().parent

INSTRUCTIONS = (
    "Thom's workout data. Read history before planning. Exercise names are free text: use "
    "exercise_names to spot synonyms. Always dry-run assign_workout/update_workout, show Thom the "
    "result, and only call again with write=True once he approves."
)
AUTH = False  # set when serving with sign-in; then current_uid() comes only from the token
_db = None


def db():
    global _db
    _db = _db or wilo_data.connect()
    return _db


def current_uid():
    """Whose data the tools act on. With sign-in, the signed-in user's token (never config). Without it (stdio,
    or local --http), the user in config/wilo.json. Never a tool argument: Claude doesn't choose whose data to read."""
    if AUTH:
        token = get_access_token()
        if not token or not token.subject:
            raise PermissionError('not signed in')
        return token.subject
    return wilo_data.CONFIG['uid']


def workout_schema() -> dict[str, Any]:
    """The JSON Schema every workout must match (workout → exercises → sets). Read it before writing a workout."""
    return wilo_data.SCHEMA


def recent_completed(limit: int = 5) -> dict[str, Any]:
    """Thom's most recent completed workouts, newest first, with every set (lbs, reps, done, custom)."""
    return {'workouts': wilo_data.recent(db(), current_uid(), 'completed', limit)}


def recent_assigned(limit: int = 5) -> dict[str, Any]:
    """Most recently assigned (planned) workouts, newest assignedFor first. The newest is what the app loads."""
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
    """Every distinct exercise name Thom has logged, with how often and when last done.
    Names are free text: decide which ones mean the same exercise, and ask Thom when unsure."""
    return {'names': wilo_data.names(db(), current_uid())}


def assign_workout(workout: dict[str, Any], write: bool = False) -> dict[str, Any]:
    """Post a new workout to Thom's assigned list. Fills id and assignedFor if missing (assignedFor = the date
    it's for, e.g. '2026-10-08'). Validates against workout_schema. Dry run unless write=True."""
    return wilo_data.assign(db(), current_uid(), workout, write, datetime.now(timezone.utc))


def update_workout(collection: Literal['assigned', 'completed'], doc_id: str, workout: dict[str, Any],
                   write: bool = False) -> dict[str, Any]:
    """Replace an existing workout with an edited version (e.g. rename an exercise). Returns the list of
    field changes. Refuses missing docs and id changes. Dry run unless write=True."""
    return wilo_data.update(db(), current_uid(), collection, doc_id, workout, write)


TOOLS = [workout_schema, recent_completed, recent_assigned, get_workout, exercise_history, exercise_names,
         assign_workout, update_workout]


def make_server(provider=None, issuer=None):
    """The WILO MCP server. With a provider: OAuth sign-in (SDK endpoints) plus our Firebase login page."""
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
    p.add_argument('--port', type=int, default=8000)
    p.add_argument('--auth', action='store_true', help='with --http: require OAuth sign-in (Firebase Google login)')
    args = p.parse_args()
    if args.auth and not args.http:
        p.error('--auth needs --http')
    if args.auth:
        from wilo.auth import Store, WiloAuthProvider
        AUTH = True
        issuer = f'http://localhost:{args.port}'  # Firebase Auth allows localhost by default
        server = make_server(WiloAuthProvider(Store(db()), f'{issuer}/login', resource=f'{issuer}/mcp'), issuer)
    if args.http:
        # Localhost only until this is hosted behind HTTPS (#31 step C): never bind to a public interface.
        server.run(transport='streamable-http', host='127.0.0.1', port=args.port)
    else:
        server.run()


if __name__ == '__main__':
    main()
