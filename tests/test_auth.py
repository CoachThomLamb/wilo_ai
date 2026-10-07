"""Tests for wilo/auth.py: the OAuth provider behind the connector's sign-in. Fake db and a fake clock.

    .venv/bin/python -m unittest discover tests
"""

import asyncio
import unittest
from urllib.parse import parse_qs, urlparse

from mcp.server.auth.provider import AuthorizationParams, RegistrationError
from mcp.shared.auth import OAuthClientInformationFull
from test_wilo_data import FakeDB

from wilo import auth

run = asyncio.run
CLAUDE = 'https://claude.ai/api/mcp/auth_callback'


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


def client(client_id='claude', redirect=CLAUDE):
    return OAuthClientInformationFull(client_id=client_id, redirect_uris=[redirect], token_endpoint_auth_method='none',
                                      grant_types=['authorization_code', 'refresh_token'], response_types=['code'])


class ProviderTest(unittest.TestCase):
    def setUp(self):
        self.db, self.clock = FakeDB(), Clock()
        self.p = auth.WiloAuthProvider(auth.Store(self.db), 'http://localhost:8000/login', clock=self.clock)
        self.c = client()
        run(self.p.register_client(self.c))

    def sign_in(self, uid='thom', c=None):
        """authorize → login page → complete_login. Returns the code Claude receives."""
        c = c or self.c
        params = AuthorizationParams(state='xyz', scopes=['workouts'], code_challenge='challenge', redirect_uri=CLAUDE,
                                     redirect_uri_provided_explicitly=True, resource='http://localhost:8000/mcp')
        login = run(self.p.authorize(c, params))
        pending = parse_qs(urlparse(login).query)['request'][0]
        back = self.p.complete_login(pending, uid)
        q = parse_qs(urlparse(back).query)
        self.assertTrue(back.startswith(CLAUDE))
        self.assertEqual(q['state'], ['xyz'])
        return q['code'][0]

    def tokens(self, uid='thom'):
        code = run(self.p.load_authorization_code(self.c, self.sign_in(uid)))
        return run(self.p.exchange_authorization_code(self.c, code))

    # Registration
    def test_registration_allows_only_claude_and_loopback_redirects(self):
        run(self.p.register_client(client('code', 'http://localhost:51234/callback')))
        run(self.p.register_client(client('code2', 'http://127.0.0.1:9/callback')))
        for bad in ['https://evil.example/cb', 'http://192.168.1.5/cb', 'https://claude.ai/other']:
            with self.subTest(bad), self.assertRaises(RegistrationError):
                run(self.p.register_client(client('x', bad)))

    def test_registered_client_round_trips(self):
        self.assertEqual(run(self.p.get_client('claude')).redirect_uris[0].unicode_string(), CLAUDE)
        self.assertIsNone(run(self.p.get_client('nobody')))

    # Sign-in and codes
    def test_full_flow_gives_tokens_for_the_signed_in_uid(self):
        tok = self.tokens('thom')
        self.assertEqual(tok.token_type, 'Bearer')
        self.assertEqual(run(self.p.load_access_token(tok.access_token)).subject, 'thom')

    def test_login_page_shows_redirect_host(self):
        params = AuthorizationParams(state=None, scopes=None, code_challenge='c', redirect_uri=CLAUDE,
                                     redirect_uri_provided_explicitly=True, resource=None)
        pending = parse_qs(urlparse(run(self.p.authorize(self.c, params))).query)['request'][0]
        self.assertEqual(self.p.pending_redirect_host(pending), 'claude.ai')

    def test_pending_request_is_single_use_and_expires(self):
        params = AuthorizationParams(state=None, scopes=None, code_challenge='c', redirect_uri=CLAUDE,
                                     redirect_uri_provided_explicitly=True, resource=None)
        pending = parse_qs(urlparse(run(self.p.authorize(self.c, params))).query)['request'][0]
        self.p.complete_login(pending, 'thom')
        with self.assertRaises(ValueError):
            self.p.complete_login(pending, 'thom')
        pending2 = parse_qs(urlparse(run(self.p.authorize(self.c, params))).query)['request'][0]
        self.clock.t += auth.PENDING_TTL + 1
        with self.assertRaises(ValueError):
            self.p.complete_login(pending2, 'thom')

    def test_code_is_single_use(self):
        code = self.sign_in()
        loaded = run(self.p.load_authorization_code(self.c, code))
        run(self.p.exchange_authorization_code(self.c, loaded))
        self.assertIsNone(run(self.p.load_authorization_code(self.c, code)))

    def test_code_expires(self):
        code = self.sign_in()
        self.clock.t += auth.CODE_TTL + 1
        self.assertIsNone(run(self.p.load_authorization_code(self.c, code)))

    def test_code_belongs_to_its_client(self):
        other = client('other')
        run(self.p.register_client(other))
        self.assertIsNone(run(self.p.load_authorization_code(other, self.sign_in())))

    # Tokens
    def test_access_token_expires(self):
        tok = self.tokens()
        self.clock.t += auth.ACCESS_TTL + 1
        self.assertIsNone(run(self.p.load_access_token(tok.access_token)))

    def test_refresh_rotates(self):
        tok = self.tokens('thom')
        rt = run(self.p.load_refresh_token(self.c, tok.refresh_token))
        new = run(self.p.exchange_refresh_token(self.c, rt, []))
        self.assertIsNone(run(self.p.load_refresh_token(self.c, tok.refresh_token)))  # old one is dead
        self.assertEqual(run(self.p.load_access_token(new.access_token)).subject, 'thom')
        self.assertIsNotNone(run(self.p.load_refresh_token(self.c, new.refresh_token)))

    def test_refresh_token_belongs_to_its_client(self):
        other = client('other')
        run(self.p.register_client(other))
        self.assertIsNone(run(self.p.load_refresh_token(other, self.tokens().refresh_token)))

    def test_users_get_their_own_tokens(self):
        a, b = self.tokens('thom'), self.tokens('someone-else')
        self.assertEqual(run(self.p.load_access_token(a.access_token)).subject, 'thom')
        self.assertEqual(run(self.p.load_access_token(b.access_token)).subject, 'someone-else')

    def test_revoke(self):
        tok = self.tokens()
        run(self.p.revoke_token(run(self.p.load_access_token(tok.access_token))))
        self.assertIsNone(run(self.p.load_access_token(tok.access_token)))

    def test_secrets_are_stored_hashed(self):
        tok = self.tokens()
        stored = ' '.join(self.db.store)
        self.assertNotIn(tok.access_token, stored)
        self.assertNotIn(tok.refresh_token, stored)


if __name__ == '__main__':
    unittest.main()
