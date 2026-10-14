"""The tracker's voice coach routes (#78 spike): CORS, sign-in, the uid allowlist, and the upstream call.
Firebase ID-token checks and the vendor API are stubbed; nothing leaves the process.

    .venv/bin/python -m unittest discover tests
"""

import os
import unittest
from unittest import mock

import firebase_admin.auth
from starlette.testclient import TestClient

from wilo import mcp_server as srv
from wilo import voice

TRACKER = 'https://wilo2-1ee44.web.app'
TOKENS = {'thom-token': 'thom', 'stranger-token': 'stranger'}


class VoiceRoutesBase(unittest.TestCase):
    route = None  # set by each option's test class

    def setUp(self):
        self.saved = srv.db, firebase_admin.auth.verify_id_token
        srv.db = lambda: None
        firebase_admin.auth.verify_id_token = lambda tok: {'uid': TOKENS[tok]}
        self.env = mock.patch.dict(os.environ, {'WILO_VOICE_UIDS': 'thom'})
        self.env.start()
        self.http = TestClient(srv.make_server().streamable_http_app()).__enter__()

    def tearDown(self):
        self.http.__exit__(None, None, None)
        self.env.stop()
        srv.db, firebase_admin.auth.verify_id_token = self.saved

    def post(self, token='thom-token', origin=TRACKER, **kw):
        headers = {'origin': origin, **({'authorization': f'Bearer {token}'} if token else {})}
        return self.http.post(self.route, headers=headers, **kw)

    def check_guard(self):
        pre = self.http.options(self.route, headers={'origin': TRACKER, 'access-control-request-method': 'POST'})
        self.assertEqual(pre.status_code, 204)
        self.assertEqual(pre.headers['access-control-allow-origin'], TRACKER)
        self.assertIn('authorization', pre.headers['access-control-allow-headers'])
        # PR previews and localhost are tracker origins too; other sites get no CORS header.
        for origin in ('https://wilo2-1ee44--pr74-feat-x.web.app', 'http://localhost:5000'):
            self.assertEqual(self.http.options(self.route, headers={'origin': origin}).headers.get('access-control-allow-origin'), origin)
        self.assertNotIn('access-control-allow-origin', self.http.options(self.route, headers={'origin': 'https://evil.example'}).headers)
        self.assertEqual(self.post(token=None).status_code, 401)
        self.assertEqual(self.post(token='stranger-token').status_code, 401)  # signed in, not on the allowlist
        with mock.patch.dict(os.environ, {'WILO_VOICE_UIDS': ''}):
            self.assertEqual(self.post().status_code, 401)  # unset allowlist = nobody


class ToolsTest(unittest.TestCase):
    def test_tools_match_across_vendors(self):
        names = [t[0] for t in voice.TOOLS]
        self.assertEqual([t['name'] for t in voice.openai_tools()], names)
        self.assertEqual([t['name'] for t in voice.claude_tools()], names)
        for t in voice.openai_tools():
            self.assertEqual(t['type'], 'function')
            self.assertEqual(t['parameters']['type'], 'object')
            self.assertTrue(set(t['parameters']['required']) <= set(t['parameters']['properties']))


def block(**kw):
    return mock.Mock(**kw)


class CoachTurnTest(VoiceRoutesBase):
    route = '/coach/turn'

    def test_guard(self):
        self.check_guard()

    def turn(self, content, stop_reason='end_turn', **body):
        create = mock.AsyncMock(return_value=mock.Mock(content=content, stop_reason=stop_reason))
        with mock.patch('anthropic.AsyncAnthropic') as client:
            client.return_value.beta.messages.create = create
            r = self.post(json={'text': 'drop bench to 175', 'workout': {'name': 'Push'}, **body})
        return r, create

    def test_returns_speech_and_ops_for_the_tracker(self):
        text = block(type='text', text='Dropped bench to 175.')
        call = block(type='tool_use', input={'exercise': 1, 'set': 1, 'lbs': 175})
        call.name = 'update_set'  # Mock(name=...) names the mock itself
        history = [{'role': 'assistant', 'content': 'stray'}, {'role': 'user', 'content': 'hi'},
                   {'role': 'assistant', 'content': 'Hey.'}, {'role': 'user', 'content': 'dangling'}, 'junk']
        r, create = self.turn([text, call], 'tool_use', history=history)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {'say': 'Dropped bench to 175.',
                                    'ops': [{'name': 'update_set', 'args': {'exercise': 1, 'set': 1, 'lbs': 175}}]})
        self.assertEqual(r.headers['access-control-allow-origin'], TRACKER)
        kw = create.call_args.kwargs
        self.assertEqual([m['role'] for m in kw['messages']], ['user', 'assistant', 'user'])  # cleaned history + this turn
        self.assertIn('<workout>{"name": "Push"}</workout>', kw['messages'][-1]['content'])
        self.assertEqual({t['name'] for t in kw['tools']}, {t[0] for t in voice.TOOLS})
        self.assertEqual(kw['fallbacks'], 'default')

    def test_refusal_empty_and_upstream_errors(self):
        r, _ = self.turn([], 'refusal')
        self.assertEqual(r.json()['ops'], [])
        self.assertEqual(self.post(json={'text': '  '}).status_code, 400)
        with mock.patch('anthropic.AsyncAnthropic') as client:
            client.return_value.beta.messages.create = mock.AsyncMock(side_effect=RuntimeError('overloaded'))
            r = self.post(json={'text': 'hi'})
        self.assertEqual(r.status_code, 502)
        self.assertIn('overloaded', r.json()['error'])


if __name__ == '__main__':
    unittest.main()
