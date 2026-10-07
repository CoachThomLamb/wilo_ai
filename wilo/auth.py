"""
OAuth for the WILO connector (#31 step C, design: docs/connector-sign-in.md).

The MCP SDK serves the OAuth endpoints (/register, /authorize, /token, metadata) and checks PKCE,
client auth and exact redirect URIs. This module is the provider behind them: it stores clients,
pending sign-ins, codes and tokens, and does the login step. Login reuses the tracker's Firebase
Google sign-in, so a token's `subject` is the same uid the tracker uses.

Storage: Firestore collections oauth_clients, oauth_pending, oauth_codes, oauth_access, oauth_refresh.
Secrets (codes, tokens, pending IDs) are stored only as sha256 hashes. All docs expire.
"""

import hashlib
import secrets
import time
from urllib.parse import urlparse

from mcp.server.auth.provider import (
    AccessToken, AuthorizationCode, AuthorizationParams, OAuthAuthorizationServerProvider,
    RefreshToken, RegistrationError, construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

SCOPE = 'workouts'
CLAUDE_CALLBACK = 'https://claude.ai/api/mcp/auth_callback'
PENDING_TTL, CODE_TTL, ACCESS_TTL, REFRESH_TTL = 600, 300, 3600, 30 * 24 * 3600


def _hash(secret):
    return hashlib.sha256(secret.encode()).hexdigest()


def allowed_redirect(uri):
    """Claude's hosted callback, or a loopback redirect (Claude Code) on any port."""
    u = urlparse(str(uri))
    return str(uri) == CLAUDE_CALLBACK or (u.scheme == 'http' and u.hostname in ('localhost', '127.0.0.1'))


class Store:
    """Hashed-key docs in Firestore (or the fake db in tests)."""

    def __init__(self, db):
        self.db = db

    def _ref(self, kind, key):
        return self.db.collection(f'oauth_{kind}').document(key)

    def put(self, kind, key, doc):
        self._ref(kind, key).set(doc)

    def get(self, kind, key, now):
        snap = self._ref(kind, key).get()
        doc = snap.to_dict() if snap.exists else None
        if doc and doc.get('expires_at') is not None and doc['expires_at'] < now:
            self.delete(kind, key)
            return None
        return doc

    def delete(self, kind, key):
        self._ref(kind, key).delete()


class WiloAuthProvider(OAuthAuthorizationServerProvider):
    def __init__(self, store, login_url, resource=None, clock=time.time):
        # resource: this server's MCP URL. Tokens record it, and the server refuses tokens for any other resource
        # (AuthSettings.validate_token_resource). Used when a client doesn't send `resource`.
        self.store, self.login_url, self.resource, self.clock = store, login_url, resource, clock

    # Clients (dynamic client registration)
    async def get_client(self, client_id):
        doc = self.store.get('clients', client_id, self.clock())
        return OAuthClientInformationFull.model_validate(doc) if doc else None

    async def register_client(self, client_info):
        bad = [str(u) for u in client_info.redirect_uris or [] if not allowed_redirect(u)]
        if not client_info.redirect_uris or bad:
            raise RegistrationError(error='invalid_redirect_uri', error_description=f'redirect URI not allowed: {bad}')
        self.store.put('clients', client_info.client_id, client_info.model_dump(mode='json', exclude_none=True))

    # Authorization: park the request, send the user to the login page
    async def authorize(self, client, params: AuthorizationParams):
        pending = secrets.token_urlsafe(32)
        self.store.put('pending', _hash(pending), {
            'client_id': client.client_id, 'redirect_uri': str(params.redirect_uri),
            'redirect_uri_provided_explicitly': params.redirect_uri_provided_explicitly,
            'code_challenge': params.code_challenge, 'scopes': params.scopes or [SCOPE],
            'state': params.state, 'resource': params.resource or self.resource, 'expires_at': self.clock() + PENDING_TTL,
        })
        return f'{self.login_url}?request={pending}'

    def pending_redirect_host(self, pending):
        """For the login page: which host the user is about to be sent back to."""
        doc = self.store.get('pending', _hash(pending), self.clock())
        return urlparse(doc['redirect_uri']).hostname if doc else None

    def complete_login(self, pending, uid):
        """After Firebase sign-in: turn the parked request into a code for `uid`. Returns the redirect URL."""
        key = _hash(pending)
        p = self.store.get('pending', key, self.clock())
        if not p:
            raise ValueError('sign-in request expired or unknown')
        self.store.delete('pending', key)  # single use
        code = secrets.token_urlsafe(32)
        self.store.put('codes', _hash(code), {
            'scopes': p['scopes'], 'expires_at': self.clock() + CODE_TTL, 'client_id': p['client_id'],
            'code_challenge': p['code_challenge'], 'redirect_uri': p['redirect_uri'],
            'redirect_uri_provided_explicitly': p['redirect_uri_provided_explicitly'],
            'resource': p['resource'], 'subject': uid,
        })
        return construct_redirect_uri(p['redirect_uri'], code=code, state=p['state'])

    async def load_authorization_code(self, client, authorization_code):
        doc = self.store.get('codes', _hash(authorization_code), self.clock())
        if not doc or doc['client_id'] != client.client_id:
            return None
        return AuthorizationCode(code=authorization_code, **doc)

    async def exchange_authorization_code(self, client, authorization_code):
        self.store.delete('codes', _hash(authorization_code.code))  # single use
        return self._issue(client.client_id, authorization_code.scopes, authorization_code.resource,
                           authorization_code.subject)

    # Tokens
    def _issue(self, client_id, scopes, resource, uid):
        now = self.clock()
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        base = {'client_id': client_id, 'scopes': scopes, 'resource': resource, 'subject': uid}
        self.store.put('access', _hash(access), {**base, 'expires_at': int(now + ACCESS_TTL)})
        self.store.put('refresh', _hash(refresh), {**base, 'expires_at': int(now + REFRESH_TTL)})
        return OAuthToken(access_token=access, token_type='Bearer', expires_in=ACCESS_TTL,
                          scope=' '.join(scopes), refresh_token=refresh)

    async def load_refresh_token(self, client, refresh_token):
        doc = self.store.get('refresh', _hash(refresh_token), self.clock())
        if not doc or doc['client_id'] != client.client_id:
            return None
        return RefreshToken(token=refresh_token, **doc)

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        self.store.delete('refresh', _hash(refresh_token.token))  # rotate: the old one stops working
        return self._issue(client.client_id, scopes or refresh_token.scopes, refresh_token.resource,
                           refresh_token.subject)

    async def load_access_token(self, token):
        doc = self.store.get('access', _hash(token), self.clock())
        return AccessToken(token=token, **doc) if doc else None

    async def revoke_token(self, token):
        self.store.delete('access', _hash(token.token))
        self.store.delete('refresh', _hash(token.token))
