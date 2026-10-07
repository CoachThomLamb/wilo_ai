"""End-to-end sign-in over HTTP, in-process: the OAuth dance Claude does against `wilo.mcp_server --http --auth`.
Fake db (no Firestore) and a stubbed Firebase ID-token check.

    .venv/bin/python -m unittest discover tests
"""

import base64
import hashlib
import secrets
import sys
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

import firebase_admin.auth
from mcp.server.mcpserver import MCPServer
from starlette.testclient import TestClient
from test_wilo_data import FakeDB

from wilo import auth
from wilo import mcp_server as srv

ISSUER = 'http://localhost:8000'
CLAUDE = 'https://claude.ai/api/mcp/auth_callback'


def pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    return verifier, challenge


class SignInOverHttpTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.provider = auth.WiloAuthProvider(auth.Store(self.db), f'{ISSUER}/login', resource=f'{ISSUER}/mcp')
        self.saved = srv.db, firebase_admin.auth.verify_id_token, srv.AUTH
        srv.db = lambda: self.db
        firebase_admin.auth.verify_id_token = lambda tok: {'uid': {'good-firebase-token': 'thom'}[tok]}
        srv.AUTH = True
        # As a context manager, so the app's lifespan (the MCP session manager) runs, as under uvicorn.
        self.http = TestClient(srv.make_server(self.provider, ISSUER).streamable_http_app(), base_url=ISSUER).__enter__()

    def tearDown(self):
        self.http.__exit__(None, None, None)
        srv.db, firebase_admin.auth.verify_id_token, srv.AUTH = self.saved

    def register(self, redirect=CLAUDE):
        return self.http.post('/register', json={'redirect_uris': [redirect], 'token_endpoint_auth_method': 'none',
                                                 'grant_types': ['authorization_code', 'refresh_token'],
                                                 'response_types': ['code'], 'client_name': 'Claude'})

    def sign_in(self, resource=f'{ISSUER}/mcp'):
        """Register → authorize → login page → Firebase callback. Returns (client_id, code, verifier)."""
        client_id = self.register().json()['client_id']
        verifier, challenge = pkce()
        r = self.http.get('/authorize', params={
            'response_type': 'code', 'client_id': client_id, 'redirect_uri': CLAUDE, 'code_challenge': challenge,
            'code_challenge_method': 'S256', 'state': 'st8', 'scope': 'workouts',
            **({'resource': resource} if resource else {})},
            follow_redirects=False)
        self.assertIn(r.status_code, (302, 307))
        login = r.headers['location']
        self.assertTrue(login.startswith(f'{ISSUER}/login?request='))
        pending = parse_qs(urlparse(login).query)['request'][0]
        page = self.http.get('/login', params={'request': pending})
        self.assertEqual(page.status_code, 200)
        self.assertIn('claude.ai', page.text)
        back = self.http.post('/login/callback', json={'request': pending, 'idToken': 'good-firebase-token'}).json()['redirect']
        q = parse_qs(urlparse(back).query)
        self.assertTrue(back.startswith(CLAUDE))
        self.assertEqual(q['state'], ['st8'])
        return client_id, q['code'][0], verifier

    def token(self, client_id, code, verifier):
        return self.http.post('/token', data={'grant_type': 'authorization_code', 'code': code, 'redirect_uri': CLAUDE,
                                              'client_id': client_id, 'code_verifier': verifier})

    # Discovery
    def test_unauthenticated_mcp_gets_401_pointing_at_metadata(self):
        r = self.http.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
        self.assertEqual(r.status_code, 401)
        self.assertIn('resource_metadata=', r.headers.get('www-authenticate', ''))

    def test_protected_resource_metadata(self):
        url = self.http.post('/mcp', json={}).headers['www-authenticate'].split('resource_metadata="')[1].split('"')[0]
        meta = self.http.get(url).json()
        self.assertEqual(meta['resource'].rstrip('/'), f'{ISSUER}/mcp')
        self.assertEqual(meta['authorization_servers'][0].rstrip('/'), ISSUER)

    def test_authorization_server_metadata(self):
        meta = self.http.get('/.well-known/oauth-authorization-server').json()
        self.assertEqual(meta['code_challenge_methods_supported'], ['S256'])
        self.assertTrue(meta['registration_endpoint'].endswith('/register'))

    # Registration and login page
    def test_register_rejects_foreign_redirects(self):
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.register('http://localhost:51234/callback').status_code, 201)  # Claude Code
        self.assertEqual(self.register('https://evil.example/cb').status_code, 400)

    def test_login_page_rejects_unknown_requests_without_echoing_them(self):
        evil = '<script>alert(1)</script>'
        r = self.http.get('/login', params={'request': evil})
        self.assertEqual(r.status_code, 400)
        self.assertNotIn('<script>alert', r.text)
        self.assertEqual(self.http.get('/login', params={'request': 'A' * 43}).status_code, 400)

    def test_bad_firebase_token_is_refused(self):
        client_id = self.register().json()['client_id']
        _, challenge = pkce()
        r = self.http.get('/authorize', params={'response_type': 'code', 'client_id': client_id, 'redirect_uri': CLAUDE,
                                                'code_challenge': challenge, 'code_challenge_method': 'S256'},
                          follow_redirects=False)
        pending = parse_qs(urlparse(r.headers['location']).query)['request'][0]
        self.assertEqual(self.http.post('/login/callback', json={'request': pending, 'idToken': 'forged'}).status_code, 400)

    # Tokens and tool access
    def test_full_sign_in_then_tools_work_as_the_signed_in_user(self):
        client_id, code, verifier = self.sign_in()
        tok = self.token(client_id, code, verifier)
        self.assertEqual(tok.status_code, 200, tok.text)
        access = tok.json()['access_token']
        r = self.http.post('/mcp', headers={'Authorization': f'Bearer {access}', 'Accept': 'application/json, text/event-stream'},
                           json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                               'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 't', 'version': '1'}}})
        self.assertEqual(r.status_code, 200, r.text)  # past sign-in, and the MCP session started
        self.assertEqual(self._uid_for(access), 'thom')

    def _uid_for(self, access):
        """current_uid() as a tool sees it, for a request carrying this access token."""
        import asyncio
        from mcp.server.auth.middleware.auth_context import auth_context_var
        from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
        token = asyncio.run(self.provider.load_access_token(access))
        reset = auth_context_var.set(AuthenticatedUser(token))
        try:
            return srv.current_uid()
        finally:
            auth_context_var.reset(reset)

    def call_mcp(self, access):
        return self.http.post('/mcp', headers={'Authorization': f'Bearer {access}', 'Accept': 'application/json, text/event-stream'},
                              json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                                  'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 't', 'version': '1'}}})

    def test_token_for_another_resource_is_refused(self):
        client_id, code, verifier = self.sign_in(resource='https://other.example/mcp')
        access = self.token(client_id, code, verifier).json()['access_token']
        self.assertEqual(self.call_mcp(access).status_code, 401)

    def test_client_without_resource_still_works(self):
        client_id, code, verifier = self.sign_in(resource=None)
        access = self.token(client_id, code, verifier).json()['access_token']
        self.assertEqual(self.call_mcp(access).status_code, 200)

    def test_without_a_token_current_uid_refuses(self):
        with self.assertRaises(PermissionError):
            srv.current_uid()

    def test_wrong_pkce_verifier_is_refused(self):
        client_id, code, _ = self.sign_in()
        r = self.token(client_id, code, 'not-the-verifier-' + 'x' * 40)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error'], 'invalid_grant')

    def test_code_cannot_be_used_twice(self):
        client_id, code, verifier = self.sign_in()
        self.assertEqual(self.token(client_id, code, verifier).status_code, 200)
        self.assertEqual(self.token(client_id, code, verifier).status_code, 400)

    def test_refresh_rotates_over_http(self):
        client_id, code, verifier = self.sign_in()
        old = self.token(client_id, code, verifier).json()['refresh_token']
        r = self.http.post('/token', data={'grant_type': 'refresh_token', 'refresh_token': old, 'client_id': client_id})
        self.assertEqual(r.status_code, 200, r.text)
        again = self.http.post('/token', data={'grant_type': 'refresh_token', 'refresh_token': old, 'client_id': client_id})
        self.assertEqual(again.status_code, 400)
        self.assertEqual(again.json()['error'], 'invalid_grant')


class MainSwitchesToSignInTest(unittest.TestCase):
    """`--http --auth` must switch the module-level server and current_uid() to sign-in mode. Inside main() that
    needs `global`; without it they'd be locals and tools would silently fall back to the config uid."""

    def test_main_with_auth_turns_sign_in_on(self):
        saved = srv.AUTH, srv.server, srv.db
        fake = FakeDB()
        try:
            srv.db = lambda: fake
            with mock.patch.object(sys, 'argv', ['wilo.mcp_server', '--http', '--auth', '--port', '8999']), \
                 mock.patch.object(MCPServer, 'run', autospec=True) as run:
                srv.main()
            self.assertTrue(srv.AUTH)
            self.assertIs(run.call_args.args[0], srv.server)  # the sign-in server is the one that runs
            self.assertIsNotNone(srv.server._auth_server_provider)
            with self.assertRaises(PermissionError):
                srv.current_uid()  # no token: refused, no fallback to config
        finally:
            srv.AUTH, srv.server, srv.db = saved


if __name__ == '__main__':
    unittest.main()
