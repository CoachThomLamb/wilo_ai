"""
Voice coach in the tracker (#78 spike). The tracker's mic button talks to these routes on the connector
server, with the signed-in user's Firebase ID token as a Bearer token.

The coach changes the workout on screen through tracker tools (TOOLS below). The tracker runs them
(window.wiloTracker.apply in fe/index.html); nothing here writes to Firestore. The workout is saved by
Finish, as always.

Spend guard: only uids listed in WILO_VOICE_UIDS (comma-separated) may use voice. Unset means nobody.
"""

import json
import os
import re

from starlette.responses import JSONResponse, Response

# The tracker's origins: Hosting (live and PR previews) and local testing.
ALLOWED_ORIGIN = re.compile(r'https://wilo2-1ee44(--[a-z0-9-]+)?\.(web\.app|firebaseapp\.com)|http://(localhost|127\.0\.0\.1)(:\d+)?')

COACH_PROMPT = """You are Thom's strength coach, talking with him by voice while he works out. He's looking at
his workout on his phone.

- Keep every reply to one or two short spoken sentences. No lists, no markdown.
- When he asks for a change, make it with the tools right away and say what you changed. The screen updates
  as you call them; there's no dry run. Saving happens when he taps Finish.
- Exercise and set numbers start at 1, as on his screen. Each tool returns the workout as it is now; use the
  latest one, since he also edits by hand.
- If he logs a set out loud ("185 for 8"), update the next set that isn't done and mark it done.
- Respect pain: if something hurts, offer an easier swap rather than pushing through."""

_EXERCISE = {'type': 'integer', 'minimum': 1, 'description': 'Exercise number, from 1, as on screen.'}
_SET = {'type': 'integer', 'minimum': 1, 'description': 'Set number within the exercise, from 1.'}
_LBS = {'type': 'number', 'minimum': 0, 'description': 'Weight in lbs.'}
_REPS = {'type': 'number', 'minimum': 0, 'description': 'Reps (seconds for timed exercises).'}

# Neutral form: name, description, JSON Schema. openai_tools() / claude_tools() reshape it per vendor.
TOOLS = [
    ('get_workout', 'The workout on screen now: exercises, sets, what is done.', {}, []),
    ('update_set', 'Change one set: weight, reps, or done. Leave out what stays the same.',
     {'exercise': _EXERCISE, 'set': _SET, 'lbs': _LBS, 'reps': _REPS, 'done': {'type': 'boolean'}}, ['exercise', 'set']),
    ('add_set', 'Add a set to the end of an exercise. Copies the last set unless lbs/reps are given.',
     {'exercise': _EXERCISE, 'lbs': _LBS, 'reps': _REPS}, ['exercise']),
    ('remove_set', 'Remove one set from an exercise.', {'exercise': _EXERCISE, 'set': _SET}, ['exercise', 'set']),
    ('edit_exercise', "Rename an exercise or change its cue (the coach's note under the name).",
     {'exercise': _EXERCISE, 'name': {'type': 'string'}, 'cue': {'type': 'string'}}, ['exercise']),
    ('add_exercise', 'Add an exercise. after = the exercise number to put it after (0 = first); default last.',
     {'name': {'type': 'string'}, 'sets': {'type': 'integer', 'minimum': 1}, 'reps': _REPS, 'lbs': _LBS,
      'cue': {'type': 'string'}, 'after': {'type': 'integer', 'minimum': 0}}, ['name']),
    ('remove_exercise', 'Remove an exercise from the workout.', {'exercise': _EXERCISE}, ['exercise']),
]


def _schema(props, required):
    return {'type': 'object', 'properties': props, 'required': required}


def openai_tools():
    return [{'type': 'function', 'name': n, 'description': d, 'parameters': _schema(p, r)} for n, d, p, r in TOOLS]


def claude_tools():
    return [{'name': n, 'description': d, 'input_schema': _schema(p, r)} for n, d, p, r in TOOLS]


def cors_headers(request):
    origin = request.headers.get('origin', '')
    if not ALLOWED_ORIGIN.fullmatch(origin):
        return {}
    return {'Access-Control-Allow-Origin': origin, 'Access-Control-Allow-Headers': 'authorization, content-type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Max-Age': '600', 'Vary': 'Origin'}


def signed_in_uid(request, init_firebase):
    """The caller's uid from their Firebase ID token. PermissionError if missing, bad, or not allowed to use voice."""
    from firebase_admin import auth as firebase_auth
    header = request.headers.get('authorization', '')
    if not header.startswith('Bearer '):
        raise PermissionError('not signed in')
    init_firebase()
    try:
        uid = firebase_auth.verify_id_token(header.removeprefix('Bearer '))['uid']
    except Exception as err:  # expired, revoked, malformed
        raise PermissionError(f'bad sign-in token: {err}') from err
    allowed = {u.strip() for u in os.environ.get('WILO_VOICE_UIDS', '').split(',') if u.strip()}
    if uid not in allowed:
        raise PermissionError('voice is not enabled for this account')
    return uid


def guarded(init_firebase, handler):
    """Wraps a route: CORS preflight, then sign-in, then handler(request, uid). Errors come back as JSON."""
    async def route(request):
        headers = cors_headers(request)
        if request.method == 'OPTIONS':
            return Response(status_code=204, headers=headers)
        try:
            uid = signed_in_uid(request, init_firebase)
        except PermissionError as err:
            return JSONResponse({'error': str(err)}, status_code=401, headers=headers)
        try:
            response = await handler(request, uid)
        except Exception as err:  # upstream API down, bad key, malformed body
            return JSONResponse({'error': str(err)}, status_code=502, headers=headers)
        response.headers.update(headers)
        return response
    return route


# ---- option 2: Claude, one turn at a time -----------------------------------------------------------------
# The browser turns speech into text (Web Speech API), posts it here with the workout on screen and the
# recent conversation, and speaks the reply. Claude's tool calls come back as ops for the tracker to run;
# they aren't run here, so one request is one turn.
COACH_MODEL = os.environ.get('WILO_COACH_MODEL', 'claude-opus-5-5')
HISTORY_TURNS = 12


def clean_history(history):
    """Text-only turns, alternating, starting with the user. Anything else from the browser is dropped."""
    turns = [{'role': t['role'], 'content': t['content']} for t in (history or [])[-HISTORY_TURNS:]
             if isinstance(t, dict) and t.get('role') in ('user', 'assistant') and isinstance(t.get('content'), str)]
    out = []
    for t in turns:
        if (out and out[-1]['role'] == t['role']) or (not out and t['role'] != 'user'):
            continue
        out.append(t)
    return out[:-1] if out and out[-1]['role'] == 'user' else out


async def coach_turn(request, uid):
    import anthropic  # reads ANTHROPIC_API_KEY
    body = await request.json()
    text = str(body.get('text', '')).strip()
    if not text:
        return JSONResponse({'error': 'nothing was said'}, status_code=400)
    prompt = f"<workout>{json.dumps(body.get('workout', {}))}</workout>\n\n{text}"
    reply = await anthropic.AsyncAnthropic().beta.messages.create(
        model=COACH_MODEL, max_tokens=4096, system=COACH_PROMPT, tools=claude_tools(),
        messages=clean_history(body.get('history')) + [{'role': 'user', 'content': prompt}],
        output_config={'effort': 'low'},  # short spoken turns; latency matters more than depth
        betas=['server-side-fallback-2026-07-01'], fallbacks='default')
    if reply.stop_reason == 'refusal':
        return JSONResponse({'say': "I can't help with that one.", 'ops': []})
    say = ' '.join(b.text for b in reply.content if b.type == 'text').strip()
    ops = [{'name': b.name, 'args': b.input} for b in reply.content if b.type == 'tool_use']
    return JSONResponse({'say': say or ('Done.' if ops else ''), 'ops': ops})


def add_routes(s, init_firebase):
    s.custom_route('/coach/turn', methods=['POST', 'OPTIONS'])(guarded(init_firebase, coach_turn))
