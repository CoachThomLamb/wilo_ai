"""
Coach chat inside the tracker: POST /chat on the connector server (phase 1 of the "Willow is the home" pivot).

The tracker sends {message, chatId?} with the user's Firebase ID token. The server runs Claude over the same
tools the connector serves (it reads them from the MCP server, so there is one list), with a context we build,
and returns the reply. Claude never picks whose data it touches: the uid comes from the verified token and is
handed to the tools through mcp_server.CHAT_UID.

    POST /chat   Authorization: Bearer <Firebase ID token>
                 {"message": "...", "chatId": "<from an earlier reply, or omitted for a new chat>",
                  "screen": <optional: the workout on the tracker's screen, see screen_line>}
              →  {"chatId": "...", "reply": "...", "tools": ["recent_workouts", ...]}

Who may use it: WILO_CHAT_UIDS (comma-separated), default the uid in config/wilo.json. It spends our API key,
so it is not open to every Google account that can sign in. Each user also has a daily cap (WILO_CHAT_DAILY_LIMIT).

Storage (server only; browsers are denied everything outside users/{uid} by firestore.rules):
    chat_threads/{chatId}               uid, createdAt, context (frozen when the chat starts)
    chat_threads/{chatId}/turns/{0001}  messages: the turn's API messages as a JSON string (Firestore can't
                                        hold nested arrays). Append-only, so earlier turns, thinking blocks
                                        included, go back to the API byte for byte.
    chat_threads/{chatId}/usage/{at}    uid, at, calls: one per model call (model, stop, usage as the API reports
                                        it, tools called). Every request, refusals included (#143: the real
                                        token counts; scripts/token-cost/usage_report.py adds them up).
    chat_usage/{uid}_{date}             count: requests today
    chat_spend/{uid}                    usd: what this user's chat has cost in total (for the spend cap)
    chat_feedback/{chatId}              uid, chatId, rating (bad|good|great), note?, at: "How's Wilo doing?"

Env: ANTHROPIC_API_KEY (Render dashboard), WILO_CHAT_MODEL (default claude-sonnet-5-5), WILO_CHAT_EFFORT
(default medium), WILO_CHAT_UIDS, WILO_CHAT_KIMI_UIDS + RUNPOD_API_KEY (those users chat with Kimi, #228;
WILO_CHAT_KIMI_MODEL default kimi-k2.6), WILO_CHAT_DAILY_LIMIT (default 100), WILO_CHAT_SPEND_LIMIT (dollars per user,
default 5), WILO_CHAT_UNCAPPED (no spend cap; default the config uid), WILO_TZ (default America/Toronto).
"""

import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import anthropic
import httpx

from wilo import data as wilo_data
from wilo import token_cost

# The chat's cache lasts an hour, not the default 5 minutes (#143). A message after a rest longer than 5 minutes
# rewrote the whole chat at 1.25x input price: 54% of the bill. A 1-hour write costs 2x, once; reads are 0.1x.
CHAT_CACHE = {'type': 'ephemeral', 'ttl': '1h'}
MODEL = os.environ.get('WILO_CHAT_MODEL', 'claude-sonnet-5-5')
EFFORT = os.environ.get('WILO_CHAT_EFFORT', 'medium')
DAILY_LIMIT = int(os.environ.get('WILO_CHAT_DAILY_LIMIT', 100))
# Total a user's chat may cost us, in dollars, before the coach stops answering. A setting, not code: change it on
# Render. The owner (WILO_CHAT_UNCAPPED, default the uid in config/wilo.json) has no cap.
SPEND_LIMIT = float(os.environ.get('WILO_CHAT_SPEND_LIMIT', 5))
# What a signed-in account that isn't on WILO_CHAT_UIDS sees, right after sign-in and if it tries to chat.
WAITLIST_REPLY = ("Thanks for signing up! If you're on the invite list, your account will be activated shortly. "
                  "If you aren't, stay tuned: we'll email you once Wilo goes into public beta.")
SPEND_LIMIT_REPLY = ("You've used up the free coaching for now. Your workouts are all saved. "
                     "Thom will get in touch about keeping Wilo going.")
TZ = ZoneInfo(os.environ.get('WILO_TZ', 'America/Toronto'))
MAX_STEPS = 12  # model calls per message: enough for a read-heavy plan, a stop for a runaway loop
MAX_MESSAGE = 4000
RATINGS = ('bad', 'good', 'great')  # "How's Wilo doing?" in the chat (POST /chat/feedback)
# After an hour with no message the chat's cache has expired, so carrying the chat on would rewrite all of it at 2x
# (#143: a chat kept all day cost more after each gap than the rest of it). Start a fresh one instead; the coach
# reads the user's data through the tools anyway.
IDLE = timedelta(hours=1)
BETAS = ['server-side-fallback-2026-07-01']  # with fallbacks='default': a declined request reruns on another model
# Kimi on RunPod's pay-per-token public endpoint (OpenAI format) for the uids in WILO_CHAT_KIMI_UIDS (#228): does an
# open model coach well enough, for less? Same tools, same coach.md, and the chat is stored in the same shape.
KIMI_URL = os.environ.get('WILO_CHAT_KIMI_URL', 'https://api.runpod.ai/v2/moonshot-kimi/openai/v1/chat/completions')
KIMI_MODEL = os.environ.get('WILO_CHAT_KIMI_MODEL', 'kimi-k2.6')

# The tracker's own hosts (live and PR previews) and local testing.
ORIGIN = re.compile(r'https://wilo2-1ee44(--[a-z0-9-]+)?\.(web\.app|firebaseapp\.com)|https://(www\.)?hiwilo\.com'
                    r'|http://(localhost|127\.0\.0\.1)(:\d+)?')

# Where this chat runs (client-specific). How to coach lives only in coach.md, appended below.
ROLE = """You are Wilo, chatting with the user inside the WILO Tracker on their phone, often at the gym.
Follow the coaching method below."""

_client = None
_tools = None


def client():
    global _client
    _client = _client or anthropic.AsyncAnthropic()
    return _client


def allowed_uids():
    return {u.strip() for u in os.environ.get('WILO_CHAT_UIDS', wilo_data.CONFIG['uid']).split(',') if u.strip()}


def kimi_uids():
    return {u.strip() for u in os.environ.get('WILO_CHAT_KIMI_UIDS', '').split(',') if u.strip()}


def engine_for(uid):
    return 'kimi' if uid in kimi_uids() else 'claude'


def uncapped_uids():
    return {u.strip() for u in os.environ.get('WILO_CHAT_UNCAPPED', wilo_data.CONFIG['uid']).split(',') if u.strip()}


def spent(db, uid):
    """Dollars this user's chat has cost so far (counted since the cap shipped; earlier chats aren't in it)."""
    snap = db.collection('chat_spend').document(uid).get()
    return ((snap.to_dict() or {}).get('usd', 0) if snap.exists else 0)


def add_spend(db, uid, calls, now):
    """Add this request's cost atomically (Increment on the server), so two messages finishing together can't
    overwrite each other's spend. The check before a message is a plain read: concurrent messages can overshoot the
    cap by at most one message each, since the cost is only known after Claude answers."""
    from google.cloud.firestore import Increment
    cost = sum(token_cost.call_cost(c) for c in calls)
    db.collection('chat_spend').document(uid).set({'uid': uid, 'usd': Increment(cost), 'updated': now.isoformat()},
                                                  merge=True)


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
    outlast the default 5 minutes. The chat itself (from ctx on) is cached for an hour too, in turn() (#143)."""
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


def load_thread(db, uid, chat_id, now, engine='claude'):
    """(chat_id, ref, context, history), a new thread when chat_id is None, the chat has been idle for over IDLE,
    or it ran on the other engine (a Claude chat's signed thinking can't go to Kimi, nor Kimi's to Claude).
    None if it isn't this user's."""
    if chat_id is None:
        chat_id = secrets.token_urlsafe(12)
        ref = db.collection('chat_threads').document(chat_id)
        ctx = context(db, uid, now)
        doc = {'uid': uid, 'createdAt': now.isoformat(), 'context': ctx}
        if engine != 'claude':
            doc['engine'] = engine
        ref.set(doc)
        return chat_id, ref, ctx, []
    ref = db.collection('chat_threads').document(chat_id)
    snap = ref.get()
    if not snap.exists or snap.to_dict().get('uid') != uid:
        return None
    turns = sorted(ref.collection('turns').stream(), key=lambda s: s.id)
    last = (turns[-1].to_dict().get('at') if turns else None) or snap.to_dict().get('createdAt')
    stale = last and now - datetime.fromisoformat(last) > IDLE
    if stale or snap.to_dict().get('engine', 'claude') != engine:
        return load_thread(db, uid, None, now, engine)
    return chat_id, ref, snap.to_dict()['context'], [m for t in turns for m in json.loads(t.to_dict()['messages'])]


def screen_line(screen):
    """What the tracker has on screen (fe/index.html window.__screen) as one line before the user's message, so the
    coach knows which workout they mean and where they are in it (replaces #124). Per message, not frozen with the
    chat: one chat a day can span workouts. Facts only; how to use them is coach.md's business. '' when there's no
    workout on screen or it doesn't parse: a bad screen never blocks a message."""
    if not isinstance(screen, dict) or not screen.get('docId'):
        return ''
    clean = lambda v, n=80: ' '.join(str(v).split())[:n]
    try:
        parts = [f'workout "{clean(screen.get("name") or "")}" (docId {clean(screen["docId"], 128)})']
        at = screen.get('at')
        if screen.get('finished'):
            parts.append('finished')
        elif isinstance(at, dict):
            parts.append(f"next up: exercise {int(at['index'])} of {int(screen['exercises'])}, {clean(at['name'])}, "
                         f"set {int(at['set'])} of {int(at['sets'])}")
        parts.append(f"{int(screen['done'])} of {int(screen['sets'])} sets done")
    except (KeyError, TypeError, ValueError):
        return ''
    return '[Tracker app, not typed by the user: ' + '; '.join(parts) + ']'


def reply_text(content):
    return '\n\n'.join(b['text'] for b in content if b.get('type') == 'text' and b.get('text')).strip()


async def call_claude(ctx, messages):
    """One model call → (content blocks, stop reason, the call's record for usage)."""
    resp = await client().beta.messages.create(
        model=MODEL, max_tokens=16000, betas=BETAS, fallbacks='default',
        output_config={'effort': EFFORT}, cache_control=CHAT_CACHE,
        system=system(ctx), tools=await tools(), messages=messages)
    u = resp.usage  # input = read + write + in (in: tokens after the last cache breakpoint)
    print(f'chat: {resp.model} stop={resp.stop_reason} in={u.input_tokens} read={u.cache_read_input_tokens or 0} '
          f'write={u.cache_creation_input_tokens or 0} out={u.output_tokens}', flush=True)
    content = [b.model_dump(mode='json', exclude_none=True) for b in resp.content]
    return content, resp.stop_reason, {'model': resp.model, 'stop': resp.stop_reason,
                                       'usage': u.model_dump(mode='json', exclude_none=True),
                                       'tools': [b['name'] for b in content if b['type'] == 'tool_use']}


_kimi = None


def kimi():
    global _kimi
    if _kimi is None:
        _kimi = httpx.AsyncClient(timeout=180, headers={'Authorization': f"Bearer {os.environ.get('RUNPOD_API_KEY', '')}"})
    return _kimi


def to_openai(system_blocks, messages):
    """The stored (Anthropic-shaped) chat as OpenAI chat messages. Kimi's reasoning goes back as reasoning_content."""
    out = [{'role': 'system', 'content': '\n\n'.join(b['text'] for b in system_blocks)}]
    for m in messages:
        c = m['content']
        if isinstance(c, str):
            out.append({'role': m['role'], 'content': c})
        elif m['role'] == 'user':
            for b in c:
                if b['type'] == 'tool_result':
                    out.append({'role': 'tool', 'tool_call_id': b['tool_use_id'], 'content': b['content']})
                elif b['type'] == 'text':
                    out.append({'role': 'user', 'content': b['text']})
        else:
            msg = {'role': 'assistant', 'content': reply_text(c)}
            thinking = ''.join(b.get('thinking', '') for b in c if b['type'] == 'thinking')
            if thinking:
                msg['reasoning_content'] = thinking
            calls = [{'id': b['id'], 'type': 'function',
                      'function': {'name': b['name'], 'arguments': json.dumps(b['input'])}}
                     for b in c if b['type'] == 'tool_use']
            if calls:
                msg['tool_calls'] = calls
            out.append(msg)
    return out


def from_openai(msg):
    """An OpenAI assistant message as Anthropic-shaped content blocks (how chats are stored)."""
    content = []
    if msg.get('reasoning_content'):
        content.append({'type': 'thinking', 'thinking': msg['reasoning_content']})
    if msg.get('content'):
        content.append({'type': 'text', 'text': msg['content']})
    for c in msg.get('tool_calls') or []:
        try:
            args = json.loads(c['function'].get('arguments') or '{}')
        except ValueError:
            args = {}
        content.append({'type': 'tool_use', 'id': c['id'], 'name': c['function']['name'],
                        'input': args if isinstance(args, dict) else {}})
    return content


async def call_kimi(ctx, messages):
    """One Kimi call, same contract as call_claude."""
    oa_tools = [{'type': 'function', 'function': {'name': t['name'], 'description': t['description'],
                                                  'parameters': t['input_schema']}} for t in await tools()]
    resp = await kimi().post(KIMI_URL, json={'model': KIMI_MODEL, 'max_tokens': 16000, 'tools': oa_tools,
                                             'messages': to_openai(system(ctx), messages)})
    resp.raise_for_status()
    body = resp.json()
    choice, u = body['choices'][0], body.get('usage') or {}
    content = from_openai(choice['message'])
    stop = 'tool_use' if any(b['type'] == 'tool_use' for b in content) else 'end_turn'
    model = body.get('model') or KIMI_MODEL
    print(f"chat: {model} stop={stop} in={u.get('prompt_tokens')} out={u.get('completion_tokens')}", flush=True)
    return content, stop, {'model': model, 'stop': stop, 'tools': [b['name'] for b in content if b['type'] == 'tool_use'],
                           'usage': {'input_tokens': u.get('prompt_tokens') or 0,
                                     'output_tokens': u.get('completion_tokens') or 0, 'openai': u}}


async def turn(ctx, history, message, engine='claude'):
    """Run one user message through the model and the tools. Returns (new messages to store, reply, tools used,
    calls: each model call's usage). A refusal stores no messages, so the declined exchange never goes back."""
    call = call_kimi if engine == 'kimi' else call_claude
    new = [{'role': 'user', 'content': message}]
    used, replies, calls = [], [], []
    for _ in range(MAX_STEPS):
        content, stop, record = await call(ctx, history + new)
        calls.append(record)
        if stop == 'refusal':
            return [], "Sorry, I can't help with that one.", used, calls
        new.append({'role': 'assistant', 'content': content})
        replies.append(reply_text(content))
        if stop != 'tool_use':
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
    return new, '\n\n'.join(r for r in replies if r), used, calls


def cors(request):
    """CORS headers for the tracker's own hosts (also used by wilo/media.py)."""
    origin = request.headers.get('origin', '')
    if not ORIGIN.fullmatch(origin):
        return {}
    return {'Access-Control-Allow-Origin': origin, 'Vary': 'Origin',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Authorization, Content-Type', 'Access-Control-Max-Age': '600'}


def add_chat_routes(s):
    from starlette.responses import JSONResponse, Response

    @s.custom_route('/chat/feedback', methods=['POST', 'OPTIONS'])
    async def feedback(request):
        """The user rates a chat: {"chatId", "rating": bad|good|great, "note"?: what to do better or what made it great}. One doc
        per chat in chat_feedback/{chatId}; rating again or adding the note updates it."""
        headers = cors(request)
        if request.method == 'OPTIONS':
            return Response(status_code=204, headers=headers)
        from firebase_admin import auth as firebase_auth
        db = srv.db()
        try:
            token = request.headers.get('authorization', '').removeprefix('Bearer ').strip()
            uid = firebase_auth.verify_id_token(token)['uid']
        except Exception:
            return JSONResponse({'error': 'sign in again'}, status_code=401, headers=headers)
        try:
            body = await request.json()
            chat_id, rating, note = body['chatId'], body['rating'], body.get('note')
            assert isinstance(chat_id, str) and rating in RATINGS
            assert note is None or (isinstance(note, str) and len(note) <= MAX_MESSAGE)
        except Exception:
            return JSONResponse({'error': f'send {{"chatId", "rating": {"|".join(RATINGS)}, "note"?}}'},
                                status_code=400, headers=headers)
        snap = db.collection('chat_threads').document(chat_id).get()
        if not snap.exists or snap.to_dict().get('uid') != uid:
            return JSONResponse({'error': 'chat not found'}, status_code=404, headers=headers)
        doc = {'uid': uid, 'chatId': chat_id, 'rating': rating, 'at': datetime.now(timezone.utc).isoformat()}
        if note and note.strip():
            doc['note'] = note.strip()
        db.collection('chat_feedback').document(chat_id).set(doc, merge=True)
        return JSONResponse({'ok': True}, headers=headers)

    @s.custom_route('/chat/access', methods=['GET', 'OPTIONS'])
    async def access(request):
        """Is the coach chat open for this account? The tracker asks right after sign-in, so a new account hears
        it's on the waitlist before it types anything. {"open": bool, "message": the words to show when closed}."""
        headers = cors(request)
        if request.method == 'OPTIONS':
            return Response(status_code=204, headers=headers)
        from firebase_admin import auth as firebase_auth
        srv.db()  # initialises the Firebase app the token check needs
        try:
            token = request.headers.get('authorization', '').removeprefix('Bearer ').strip()
            uid = firebase_auth.verify_id_token(token)['uid']
        except Exception:
            return JSONResponse({'error': 'sign in again'}, status_code=401, headers=headers)
        if uid in allowed_uids():
            return JSONResponse({'open': True}, headers=headers)
        return JSONResponse({'open': False, 'message': WAITLIST_REPLY}, headers=headers)

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
            return fail(403, WAITLIST_REPLY)
        try:
            body = await request.json()
            message, chat_id = body['message'], body.get('chatId')
            assert isinstance(message, str) and 0 < len(message.strip()) <= MAX_MESSAGE
            assert chat_id is None or isinstance(chat_id, str)
        except Exception:
            return fail(400, f'send {{"message": "...", "chatId": optional}}, message up to {MAX_MESSAGE} characters')
        now = datetime.now(timezone.utc)
        capped = uid not in uncapped_uids()
        if capped and spent(db, uid) >= SPEND_LIMIT:
            return fail(402, SPEND_LIMIT_REPLY)
        if not use_quota(db, uid, now):
            return fail(429, f"that's {DAILY_LIMIT} messages today; the coach is back tomorrow")
        engine = engine_for(uid)
        thread = load_thread(db, uid, chat_id, now, engine)
        if thread is None:
            return fail(404, 'chat not found; start a new one')
        chat_id, ref, ctx, history = thread
        line = screen_line(body.get('screen'))
        reset = srv.CHAT_UID.set(uid)
        try:
            new, reply, used, calls = await turn(ctx, history, f'{line}\n{message.strip()}' if line else message.strip(),
                                                engine)
        except (anthropic.APIError, httpx.HTTPError, KeyError, ValueError) as err:
            print(f'chat: API error {err!r}', flush=True)
            return fail(502, 'the coach is unavailable right now; try again in a minute')
        finally:
            srv.CHAT_UID.reset(reset)
        ref.collection('usage').document(now.isoformat()).set({'uid': uid, 'at': now.isoformat(), 'calls': calls})
        if capped:
            add_spend(db, uid, calls, now)
        if new:
            n = len(list(ref.collection('turns').stream())) + 1
            ref.collection('turns').document(f'{n:04d}').set({'messages': json.dumps(new), 'at': now.isoformat()})
        return JSONResponse({'chatId': chat_id, 'reply': reply, 'tools': used}, headers=headers)


# Last: mcp_server imports this module while it builds its server, so it must find add_chat_routes defined.
from wilo import mcp_server as srv  # noqa: E402
