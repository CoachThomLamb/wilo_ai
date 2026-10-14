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


class RealtimeCallTest(VoiceRoutesBase):
    route = '/voice/call'

    def test_guard(self):
        self.check_guard()

    def test_swaps_offer_for_answer_with_coach_session(self):
        answer = mock.Mock(text='v=0\r\nanswer')
        create = mock.AsyncMock(return_value=answer)
        with mock.patch('openai.AsyncOpenAI') as client:
            client.return_value.realtime.calls.create = create
            r = self.post(content='v=0\r\noffer')
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.text, 'v=0\r\nanswer')
        self.assertTrue(r.headers['content-type'].startswith('application/sdp'))
        self.assertEqual(r.headers['access-control-allow-origin'], TRACKER)
        kw = create.call_args.kwargs
        self.assertEqual(kw['sdp'], 'v=0\r\noffer')
        self.assertEqual(kw['session']['type'], 'realtime')
        self.assertEqual({t['name'] for t in kw['session']['tools']}, {t[0] for t in voice.TOOLS})
        self.assertIn('coach', kw['session']['instructions'])

    def test_rejects_non_sdp_and_reports_upstream_errors(self):
        self.assertEqual(self.post(content='hello').status_code, 400)
        with mock.patch('openai.AsyncOpenAI') as client:
            client.return_value.realtime.calls.create = mock.AsyncMock(side_effect=RuntimeError('bad key'))
            r = self.post(content='v=0\r\noffer')
        self.assertEqual(r.status_code, 502)
        self.assertIn('bad key', r.json()['error'])


if __name__ == '__main__':
    unittest.main()
