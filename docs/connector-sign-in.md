# Connector sign-in design (#31 step C, option B)

**Status:** design, not built. Written 2026-10-07 from Claude's connector docs (research on #31) and the installed MCP Python SDK (v2.3). Items marked **verify** are assumptions to check while building.

## Goal
Thom (and later others) adds WILO as a custom connector in Claude, clicks **Connect**, signs in with the same Google account as the tracker, and from then on the tools act only on **his** `users/{uid}`: `current_uid()` comes from the signed-in token, not from `config/wilo.json`.

## Shape
One service, one host, two roles:
- **Resource server:** the existing MCP server at `/mcp` (Streamable HTTP, `mcp/server.py --http`).
- **Authorization server (AS):** OAuth endpoints in the same process. **The SDK provides the endpoints**; we implement a *provider* (storage and the login step).

```
Claude ──(no token)──▶ /mcp ──▶ 401 + WWW-Authenticate: Bearer resource_metadata=".../.well-known/oauth-protected-resource"
Claude ──▶ /.well-known/oauth-protected-resource        (RFC 9728: resource = .../mcp, authorization_servers = [issuer])
Claude ──▶ /.well-known/oauth-authorization-server      (RFC 8414: endpoints, S256, scopes)
Claude ──▶ /register                                    (DCR: Claude registers itself as a client)
Claude ──▶ /authorize?…&code_challenge=…(S256)          → our login page (Firebase Google sign-in)
login page ──Firebase ID token──▶ /login/callback        → verify with Admin SDK → uid → auth code → redirect to Claude
Claude ──▶ /token (code + code_verifier)                 → access token + refresh token (form-urlencoded)
Claude ──(Bearer token)──▶ /mcp tools                    → current_uid() = token's uid
```

## What the SDK gives us (checked in the installed package)
- `MCPServer(auth_server_provider=…, auth=AuthSettings(issuer_url=…, resource_server_url=…, client_registration_options=…, required_scopes=…))`
- Routes: `create_auth_routes` (metadata, `/authorize`, `/token`, `/register`, revocation) and `create_protected_resource_routes`.
- Metadata advertises `code_challenge_methods_supported: ["S256"]`, which Claude requires.
- **CIMD isn't advertised:** `client_id_metadata_document_supported` isn't set, and `token_endpoint_auth_methods_supported` is `["client_secret_post", "client_secret_basic"]` (no `"none"`). So **Claude falls back to DCR**, which is fine at our scale. Enable DCR via `ClientRegistrationOptions`.
- We implement `OAuthAuthorizationServerProvider`: `get_client`, `register_client`, `authorize`, `load_authorization_code`, `exchange_authorization_code`, `load_refresh_token`, `exchange_refresh_token`, `load_access_token`, `revoke_token` (plus `exchange_identity_assertion`, which we don't need).

## The login step: reuse Firebase sign-in
`authorize()` returns a URL to our own small login page (`/login?state=…`), which:
1. Shows **"Sign in to WILO for Claude"**, with the redirect host (`claude.ai`, or `localhost` for Claude Code) clearly visible, as the MCP spec requires.
2. Uses the same Firebase Google sign-in as `fe/auth.js`, so the user gets **the same uid as in the tracker**.
3. Posts the Firebase ID token to `/login/callback`. The server verifies it with the Admin SDK (`auth.verify_id_token`) to get the `uid`, creates the authorization code tied to that uid, client, PKCE challenge and redirect URI, and redirects to Claude.

Why this rather than a separate Google OAuth client (option A):
- **Same uid as the tracker,** with no email → uid mapping.
- **No new Google Cloud console setup for local testing:** Firebase Auth already allows `localhost`. **Verify:** that the existing Firebase web config works from a page served by the MCP server.
- One sign-in system for the whole product.

## Tokens
- **Access token:** a random opaque string, expiring after 1 hour. Store only its **hash** in Firestore `oauth/access/{hash}` → `{uid, client_id, scopes, expires_at}`. `load_access_token` looks it up.
- **Refresh token:** a random opaque string, **rotated on every use** (OAuth 2.1 for public clients). Store the hash in `oauth/refresh/{hash}`; return `invalid_grant` for unknown or expired tokens.
- **Authorization code:** single use, 5-minute expiry, bound to the PKCE challenge and redirect URI.
- **Clients (DCR):** `oauth/clients/{client_id}`.
- All `oauth/*` docs are admin-only. The Firestore rules must deny client access (part of #15 step 4).

## current_uid() with sign-in
Locally (stdio) it stays the uid from config. Over HTTP with auth, it reads the verified access token for the current request and returns its `uid`. **Verify:** how a tool reads the request's access token in SDK v2 (an auth context helper or a `Context` argument).

## Claude's requirements, and how this meets them
| Requirement | How |
|---|---|
| `401` with `resource_metadata` pointer | SDK auth middleware (**verify** the exact header) |
| `resource` equals the server URL exactly | `resource_server_url = https://<host>/mcp` |
| Our AS listed first in `authorization_servers` | One AS, our issuer |
| PKCE S256 | SDK |
| Redirects: `https://claude.ai/api/mcp/auth_callback` + loopback on any port | Accept both in `authorize` and `register`: exact match for claude.ai, port-agnostic for `localhost` and `127.0.0.1` |
| Token endpoint takes form-urlencoded; `invalid_grant` on bad refresh | SDK token handler (**verify** form parsing) + our provider errors |
| Endpoints respond within 10 s (refresh 30 s) | Firestore lookups only, no slow calls |

## Hosting (needs Blaze)
- **Cloud Run** in `wilo2-1ee44`, using Cloud Run's own service account for Firestore, so **no JSON key** on the server.
- **Idea to verify:** serve it through **Firebase Hosting rewrites** (`/mcp`, `/.well-known/*`, `/authorize`, `/token`, `/register`, `/login*` → Cloud Run). Then it lives on `wilo2-1ee44.web.app`, which Firebase Auth already allows, so no extra authorized domain. If Hosting can't route `/.well-known/*`, the `resource_metadata` pointer in the `401` still works (Claude's docs recommend it for this case).

## Test plan
1. **Unit tests** for the provider: code exchange with PKCE, wrong verifier, wrong redirect, expired code, single-use code, refresh rotation, `invalid_grant`, cross-user isolation.
2. **Local, no Blaze:** `mcp/server.py --http` with auth on `127.0.0.1`. Add it to Claude Code with `claude mcp add --transport http`, sign in through the Firebase page (loopback redirect), call `exercise_history`, and check the result is Thom's data.
3. **Hosted:** deploy, add it as a custom connector in claude.ai, connect, use it from the phone app.
4. **Before anyone else connects:** lock the Firestore rules (#15 step 4).

## Open questions
- **Scopes:** one scope (`workouts`) for everything, or `workouts:read` / `workouts:write`? Start with one.
- **Token lifetimes:** 1 h access and 30 days refresh, to start.
- **Revoking access:** a "signed in to Claude" list in the tracker? Later; for now, delete the docs in `oauth/`.
