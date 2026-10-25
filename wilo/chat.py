"""
Coach chat inside the tracker: POST /chat on the connector server (phase 1 of the "Willow is the home" pivot).

The tracker sends {message, chatId?} with the user's Firebase ID token. The server runs Claude over the same
tools the connector serves (it reads them from the MCP server, so there is one list), with a context we build,
and returns the reply. Claude never picks whose data it touches: the uid comes from the verified token and is
handed to the tools through mcp_server.CHAT_UID.

    POST /chat   Authorization: Bearer <Firebase ID token>
                 {"message": "...", "chatId": "<from an earlier reply, or omitted for a new chat>"}
              →  {"chatId": "...", "reply": "...", "tools": ["recent_completed", ...]}

Who may use it: WILO_CHAT_UIDS (comma-separated), default the uid in config/wilo.json. It spends our API key,
so it is not open to every Google account that can sign in. Each user also has a daily cap (WILO_CHAT_DAILY_LIMIT).

Storage (server only; browsers are denied everything outside users/{uid} by firestore.rules):
    chat_threads/{chatId}               uid, createdAt, context (frozen when the chat starts)
    chat_threads/{chatId}/turns/{0001}  messages: the turn's API messages as a JSON string (Firestore can't
                                        hold nested arrays). Append-only, so earlier turns, thinking blocks
                                        included, go back to the API byte for byte.
    chat_usage/{uid}_{date}             count: requests today

Env: ANTHROPIC_API_KEY (Render dashboard), WILO_CHAT_MODEL (default claude-opus-5-5), WILO_CHAT_EFFORT
(default medium), WILO_CHAT_UIDS, WILO_CHAT_DAILY_LIMIT (default 100), WILO_TZ (default America/Toronto).
"""

import json
import os
import re
import secrets
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import anthropic

from wilo import data as wilo_data

MODEL = os.environ.get('WILO_CHAT_MODEL', 'claude-opus-5-5')
EFFORT = os.environ.get('WILO_CHAT_EFFORT', 'medium')
DAILY_LIMIT = int(os.environ.get('WILO_CHAT_DAILY_LIMIT', 100))
TZ = ZoneInfo(os.environ.get('WILO_TZ', 'America/Toronto'))
MAX_STEPS = 12  # model calls per message: enough for a read-heavy plan, a stop for a runaway loop
MAX_MESSAGE = 4000
BETAS = ['server-side-fallback-2026-07-01']  # with fallbacks='default': a declined request reruns on another model

# The tracker's own hosts (live and PR previews) and local testing.
ORIGIN = re.compile(r'https://wilo2-1ee44(--[a-z0-9-]+)?\.(web\.app|firebaseapp\.com)|http://(localhost|127\.0\.0\.1)(:\d+)?')

ROLE = """You are the WILO coach, chatting with the user inside the WILO workout tracker on their phone, often at
the gym. Keep replies short and easy to read on a phone: a few lines, plain text, lists only when they help.

Use the tools to read and change their training data. The coaching method below says how to plan, review and
change workouts. Workout and profile writes are dry runs first: show the user what would change in a sentence or
two, and call again with write=True only after they say yes in this chat. Todos save immediately."""

_client = None
_tools = None


def client():
    global _client
    _client = _client or anthropic.AsyncAnthropic()
    return _client


def allowed_uids():
    return {u.strip() for u in os.environ.get('WILO_CHAT_UIDS', wilo_data.CONFIG['uid']).split(',') if u.strip()}


async def tools():
    """The connector's tools as API tool definitions, in the MCP server's order (stable, so the cache holds)."""
    global _tools
    if _tools is None:
        listed = await srv.server.list_tools()
        _tools = [{'name': t.name, 'description': t.description or '',
                   'input_schema': getattr(t, 'input_schema', None) or getattr(t, 'inputSchema', None)} for t in listed]
    return _tools


async def run_tool(name, args):
    """One tool call → a tool_result's content and whether it failed. Errors go back to Claude, not the user."""
    try:
        res = await srv.server.call_tool(name, args)
    except Exception as err:  # unknown tool, bad arguments
        return str(err), True
    structured = getattr(res, 'structured_content', None)
    text = json.dumps(structured) if structured is not None else ''.join(getattr(c, 'text', '') for c in res.content)
    return text, bool(res.is_error)


def context(db, uid, now):
    """What the coach knows when a chat starts. Frozen with the chat: changing it later would edit the prompt
    under earlier turns. The coach reads anything fresher through the tools."""
    local = now.astimezone(TZ)
    profile = wilo_data.profile(db, uid)
    return (f"Today is {local:%A %Y-%m-%d}, {local:%H:%M} in {TZ.key}.\n\n"
            f"The user's coaching profile (get_profile):\n{json.dumps(profile, default=str)}")


def system(ctx):
    """Tools + this first block are the same for every chat, so they're cached for an hour: rests between sets
    outlast the default 5 minutes. The chat itself (from ctx on) changes every turn and keeps the 5-minute cache
    set in turn(). The API wants 1-hour entries before 5-minute ones, which this order gives."""
    method = (srv.HERE / 'coach.md').read_text()
    return [{'type': 'text', 'text': f'{ROLE}\n\n# Coaching method\n\n{method}',
             'cache_control': {'type': 'ephemeral', 'ttl': '1h'}},
            {'type': 'text', 'text': ctx}]


def use_quota(db, uid, now):
    """Count this request against today's cap. False once the cap is reached."""
    ref = db.collection('chat_usage').document(f'{uid}_{now.astimezone(TZ):%Y-%m-%d}')
    snap = ref.get()
    count = (snap.to_dict() or {}).get('count', 0) if snap.exists else 0
    if count >= DAILY_LIMIT:
        return False
    ref.set({'uid': uid, 'count': count + 1})
    return True


def load_thread(db, uid, chat_id, now):
    """(chat_id, ref, context, history), a new thread when chat_id is None. None if it isn't this user's."""
    if chat_id is None:
        chat_id = secrets.token_urlsafe(12)
        ref = db.collection('chat_threads').document(chat_id)
        ctx = context(db, uid, now)
        ref.set({'uid': uid, 'createdAt': now.isoformat(), 'context': ctx})
        return chat_id, ref, ctx, []
    ref = db.collection('chat_threads').document(chat_id)
    snap = ref.get()
    if not snap.exists or snap.to_dict().get('uid') != uid:
        return None
    turns = sorted(ref.collection('turns').stream(), key=lambda s: s.id)
    return chat_id, ref, snap.to_dict()['context'], [m for t in turns for m in json.loads(t.to_dict()['messages'])]


def reply_text(content):
    return '\n\n'.join(b['text'] for b in content if b.get('type') == 'text' and b.get('text')).strip()


async def turn(ctx, history, message):
    """Run one user message through Claude and the tools. Returns (new messages to store, reply, tools used).
    A refusal stores nothing, so the declined exchange never goes back to the API."""
    new = [{'role': 'user', 'content': message}]
    used, replies = [], []
    for _ in range(MAX_STEPS):
        resp = await client().beta.messages.create(
            model=MODEL, max_tokens=16000, betas=BETAS, fallbacks='default',
            output_config={'effort': EFFORT}, cache_control={'type': 'ephemeral'},
            system=system(ctx), tools=await tools(), messages=history + new)
        u = resp.usage  # input = read + write + in (in: tokens after the last cache breakpoint)
        print(f'chat: {resp.model} stop={resp.stop_reason} in={u.input_tokens} read={u.cache_read_input_tokens or 0} '
              f'write={u.cache_creation_input_tokens or 0} out={u.output_tokens}', flush=True)
        if resp.stop_reason == 'refusal':
            return [], "Sorry, I can't help with that one.", used
        content = [b.model_dump(mode='json', exclude_none=True) for b in resp.content]
        new.append({'role': 'assistant', 'content': content})
        replies.append(reply_text(content))
        if resp.stop_reason != 'tool_use':
            break
        results = []
        for block in content:
            if block['type'] == 'tool_use':
                used.append(block['name'])
                text, failed = await run_tool(block['name'], block['input'])
                results.append({'type': 'tool_result', 'tool_use_id': block['id'], 'content': text, 'is_error': failed})
        new.append({'role': 'user', 'content': results})
    else:
        replies.append('(I stopped there: that took more steps than I allow myself. Ask me to carry on.)')
    return new, '\n\n'.join(r for r in replies if r), used


def add_chat_routes(s):
    from starlette.responses import JSONResponse, Response

    def cors(request):
        origin = request.headers.get('origin', '')
        if not ORIGIN.fullmatch(origin):
            return {}
        return {'Access-Control-Allow-Origin': origin, 'Vary': 'Origin',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Authorization, Content-Type', 'Access-Control-Max-Age': '600'}

    @s.custom_route('/chat', methods=['POST', 'OPTIONS'])
    async def chat(request):
        headers = cors(request)
        if request.method == 'OPTIONS':
            return Response(status_code=204, headers=headers)

        def fail(status, error):
            return JSONResponse({'error': error}, status_code=status, headers=headers)

        from firebase_admin import auth as firebase_auth
        db = srv.db()  # also initialises the Firebase app the token check needs
        try:
            token = request.headers.get('authorization', '').removeprefix('Bearer ').strip()
            uid = firebase_auth.verify_id_token(token)['uid']
        except Exception:
            return fail(401, 'sign in again')
        if uid not in allowed_uids():
            return fail(403, 'the coach chat is not open for this account yet')
        try:
            body = await request.json()
            message, chat_id = body['message'], body.get('chatId')
            assert isinstance(message, str) and 0 < len(message.strip()) <= MAX_MESSAGE
            assert chat_id is None or isinstance(chat_id, str)
        except Exception:
            return fail(400, f'send {{"message": "...", "chatId": optional}}, message up to {MAX_MESSAGE} characters')
        now = datetime.now(timezone.utc)
        if not use_quota(db, uid, now):
            return fail(429, f"that's {DAILY_LIMIT} messages today; the coach is back tomorrow")
        thread = load_thread(db, uid, chat_id, now)
        if thread is None:
            return fail(404, 'chat not found; start a new one')
        chat_id, ref, ctx, history = thread
        reset = srv.CHAT_UID.set(uid)
        try:
            new, reply, used = await turn(ctx, history, message.strip())
        except anthropic.APIError as err:
            print(f'chat: API error {err!r}', flush=True)
            return fail(502, 'the coach is unavailable right now; try again in a minute')
        finally:
            srv.CHAT_UID.reset(reset)
        if new:
            n = len(list(ref.collection('turns').stream())) + 1
            ref.collection('turns').document(f'{n:04d}').set({'messages': json.dumps(new), 'at': now.isoformat()})
        return JSONResponse({'chatId': chat_id, 'reply': reply, 'tools': used}, headers=headers)


# Last: mcp_server imports this module while it builds its server, so it must find add_chat_routes defined.
from wilo import mcp_server as srv  # noqa: E402
