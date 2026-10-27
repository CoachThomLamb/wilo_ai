"""Tests for wilo/chat.py: POST /chat over HTTP, in-process. Fake db, stubbed Firebase token check, and a scripted
stand-in for the Claude API (no network, no key).

    .venv/bin/python -m unittest discover tests
"""

import json
import unittest

import firebase_admin.auth
from anthropic.types.beta import BetaMessage
from starlette.testclient import TestClient
from test_wilo_data import FakeDB, MINIMAL, done

from wilo import chat
from wilo import mcp_server as srv

ME, OTHER = 'thom', 'someone-else'
TOKENS = {'my-token': ME, 'other-token': OTHER}
TRACKER = 'https://wilo2-1ee44.web.app'


def message(stop, *content):
    return BetaMessage.model_validate({
        'id': 'msg', 'type': 'message', 'role': 'assistant', 'model': chat.MODEL, 'stop_reason': stop,
        'stop_sequence': None, 'usage': {'input_tokens': 10, 'output_tokens': 5}, 'content': list(content)})


def text(t):
    return {'type': 'text', 'text': t}


def tool_use(name, args, id='tu1'):
    return {'type': 'tool_use', 'id': id, 'name': name, 'input': args}


class FakeClaude:
    """Returns the scripted responses in order and records every request."""

    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []
        self.beta = self
        self.messages = self

    async def create(self, **req):
        self.requests.append(json.loads(json.dumps(req)))  # a snapshot: the caller keeps appending to its lists
        return self.responses.pop(0)


class ChatTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB({
            f'users/{ME}/completed/a': done('Bench press', [{'lbs': 135, 'reps': 10, 'done': True}], '2026-10-01T00:00:00Z'),
            f'users/{OTHER}/completed/b': done('Bench press', [{'lbs': 225, 'reps': 5, 'done': True}], '2026-10-02T00:00:00Z'),
        })
        self.saved = srv.db, firebase_admin.auth.verify_id_token, srv.AUTH, chat._client, chat.allowed_uids
        srv.db = lambda: self.db
        firebase_admin.auth.verify_id_token = lambda tok: {'uid': TOKENS[tok]}
        srv.AUTH = True  # as hosted: outside /chat, tools would need an OAuth token
        chat.allowed_uids = lambda: {ME}
        self.http = TestClient(srv.make_server().streamable_http_app()).__enter__()

    def tearDown(self):
        self.http.__exit__(None, None, None)
        srv.db, firebase_admin.auth.verify_id_token, srv.AUTH, chat._client, chat.allowed_uids = self.saved

    def claude(self, *responses):
        chat._client = FakeClaude(*responses)
        return chat._client

    def post(self, body, token='my-token', origin=TRACKER):
        return self.http.post('/chat', json=body, headers={'Authorization': f'Bearer {token}', 'Origin': origin})

    def test_simple_reply_starts_a_chat(self):
        fake = self.claude(message('end_turn', text('Hi Thom.')))
        r = self.post({'message': 'hello'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['reply'], 'Hi Thom.')
        self.assertEqual(r.headers['access-control-allow-origin'], TRACKER)
        req = fake.requests[0]
        self.assertEqual(req['model'], chat.MODEL)
        self.assertEqual(req['fallbacks'], 'default')
        self.assertEqual(req['messages'], [{'role': 'user', 'content': 'hello'}])
        self.assertIn('Coaching method', req['system'][0]['text'])
        # Fixed prefix cached for an hour, the chat for 5 minutes (the API's default TTL) after it.
        self.assertEqual(req['system'][0]['cache_control'], {'type': 'ephemeral', 'ttl': '1h'})
        self.assertNotIn('cache_control', req['system'][1])
        self.assertEqual(req['cache_control'], {'type': 'ephemeral'})
        self.assertIn('Today is', req['system'][1]['text'])
        self.assertEqual({t['name'] for t in req['tools']}, {t.name for t in __import__('asyncio').run(srv.server.list_tools())})

    def test_each_mode_uses_its_own_model(self):
        saved = dict(chat.MODES)
        chat.MODES.update(plan=('claude-opus-5-5', 'medium'), workout=('claude-haiku-5-5', 'low'))
        try:
            fake = self.claude(message('end_turn', text('ok')), message('end_turn', text('ok')))
            chat_id = self.post({'message': 'plan my week'}).json()['chatId']
            r = self.post({'message': 'swap squats', 'chatId': chat_id, 'mode': 'workout'})
            self.assertEqual(r.json()['model'], 'claude-haiku-5-5')
            plan, workout = fake.requests
            self.assertEqual((plan['model'], plan['output_config']['effort']), ('claude-opus-5-5', 'medium'))
            self.assertEqual((workout['model'], workout['output_config']['effort']), ('claude-haiku-5-5', 'low'))
            # Haiku has no server-side fallback: sending one would fail the request.
            self.assertEqual(plan['fallbacks'], 'default')
            self.assertNotIn('fallbacks', workout)
            self.assertNotIn('betas', workout)
            self.assertEqual(self.post({'message': 'x', 'mode': 'nap'}).status_code, 400)
        finally:
            chat.MODES.update(saved)

    def test_tool_calls_act_on_the_signed_in_user(self):
        self.claude(message('tool_use', text('Checking.'), tool_use('exercise_history', {'name': 'bench'})),
                    message('end_turn', text('Last bench: 135 x 10.')))
        r = self.post({'message': 'what did I bench?'})
        self.assertEqual(r.json()['tools'], ['exercise_history'])
        result = chat._client.requests[1]['messages'][-1]['content'][0]
        self.assertFalse(result['is_error'])
        self.assertEqual([h['sets'][0]['lbs'] for h in json.loads(result['content'])['history']], [135])
        self.assertEqual(r.json()['reply'], 'Checking.\n\nLast bench: 135 x 10.')

    def test_writes_stay_dry_runs_unless_claude_passes_write(self):
        self.claude(message('tool_use', tool_use('assign_workout', {'workout': MINIMAL})), message('end_turn', text('Plan ready.')))
        self.post({'message': 'plan legs'})
        self.assertFalse([k for k in self.db.store if '/assigned/' in k])

    def test_tool_errors_go_back_to_claude(self):
        self.claude(message('tool_use', tool_use('get_workout', {'collection': 'nope', 'doc_id': 'x'})),
                    message('end_turn', text('That failed.')))
        r = self.post({'message': 'x'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(chat._client.requests[1]['messages'][-1]['content'][0]['is_error'])

    def test_next_message_replays_the_whole_chat_unchanged(self):
        first = self.claude(message('tool_use', {'type': 'thinking', 'thinking': '', 'signature': 'sig'},
                                    tool_use('recent_completed', {})),
                            message('end_turn', text('You benched Monday.')))
        chat_id = self.post({'message': 'how am I doing?'}).json()['chatId']
        second = self.claude(message('end_turn', text('Sure.')))
        self.post({'message': 'thanks', 'chatId': chat_id})
        before = first.requests[1]
        after = second.requests[0]
        self.assertEqual(after['system'], before['system'])  # the context is frozen with the chat
        self.assertEqual(after['messages'][:3], before['messages'])
        self.assertEqual(after['messages'][3]['content'][0]['text'], 'You benched Monday.')
        self.assertEqual(after['messages'][4], {'role': 'user', 'content': 'thanks'})
        self.assertEqual(after['messages'][1]['content'][0], {'type': 'thinking', 'thinking': '', 'signature': 'sig'})

    def test_refusal_stores_nothing(self):
        self.claude(message('refusal'))
        chat_id = self.post({'message': 'x'}).json()['chatId']
        nxt = self.claude(message('end_turn', text('ok')))
        self.post({'message': 'y', 'chatId': chat_id})
        self.assertEqual(nxt.requests[0]['messages'], [{'role': 'user', 'content': 'y'}])

    def test_someone_elses_chat_is_not_found(self):
        self.claude(message('end_turn', text('hi')))
        chat_id = self.post({'message': 'hello'}).json()['chatId']
        chat.allowed_uids = lambda: {ME, OTHER}
        self.assertEqual(self.post({'message': 'hi', 'chatId': chat_id}, token='other-token').status_code, 404)

    def test_refuses_bad_token_unlisted_user_and_bad_body(self):
        self.claude()
        self.assertEqual(self.post({'message': 'hi'}, token='forged').status_code, 401)
        self.assertEqual(self.post({'message': 'hi'}, token='other-token').status_code, 403)
        self.assertEqual(self.post({'message': ''}).status_code, 400)
        self.assertEqual(self.post({'message': 'x' * (chat.MAX_MESSAGE + 1)}).status_code, 400)
        self.assertEqual(chat._client.requests, [])

    def test_daily_cap(self):
        saved, chat.DAILY_LIMIT = chat.DAILY_LIMIT, 1
        try:
            self.claude(message('end_turn', text('hi')))
            self.assertEqual(self.post({'message': 'one'}).status_code, 200)
            self.assertEqual(self.post({'message': 'two'}).status_code, 429)
        finally:
            chat.DAILY_LIMIT = saved

    def test_cors_preflight_only_for_tracker_hosts(self):
        ok = self.http.options('/chat', headers={'Origin': 'https://wilo2-1ee44--pr-12-abc.web.app'})
        self.assertEqual(ok.status_code, 204)
        self.assertIn('Authorization', ok.headers['access-control-allow-headers'])
        bad = self.http.options('/chat', headers={'Origin': 'https://evil.example'})
        self.assertNotIn('access-control-allow-origin', bad.headers)

    def test_runaway_loop_stops(self):
        self.claude(*[message('tool_use', tool_use('exercise_names', {}, id=f't{i}')) for i in range(chat.MAX_STEPS)])
        r = self.post({'message': 'loop'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('more steps', r.json()['reply'])

    def test_uid_does_not_leak_out_of_chat(self):
        self.claude(message('end_turn', text('hi')))
        self.post({'message': 'hello'})
        self.assertIsNone(srv.CHAT_UID.get())


if __name__ == '__main__':
    unittest.main()
