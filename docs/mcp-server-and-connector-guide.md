# WILO MCP server and Claude connector: working guide

Read this before debugging or extending `wilo/` (the workout data engine, the MCP server, connector sign-in). It describes **how things work now** and what isn't obvious from the code. History lives in the PRs linked below, not here. Keep this file current when the code changes.

## What it is
WILO's workouts live in Firestore under `users/{uid}/assigned` (planned) and `users/{uid}/completed` (done). This package lets Claude read and write them:
- **Locally:** Claude Code runs the MCP server over stdio (`wilo` in `/mcp`). Works today, including from the phone via `/rc` (Remote Control) while the laptop is on.
- **Remotely (in progress, #31):** the same server over HTTPS with OAuth sign-in, added in claude.ai as a custom connector, so it's usable from the Claude app without the laptop. Built and verified locally; hosting needs the Firebase Blaze plan.

## Files
| File | Role |
|---|---|
| `wilo/data.py` | **The engine.** All Firestore logic: `recent`, `history`, `names`, `assign`, `update`, `validate`, `diff`, `name_matches`. Also a CLI (`python -m wilo.data …`). Knows nothing about MCP |
| `wilo/mcp_server.py` | **The adapter.** 8 tools, each a thin call into `data.py`; `current_uid()`; `make_server()`; login routes; `main()` (stdio / `--http` / `--auth`) |
| `wilo/auth.py` | **Sign-in provider** (`WiloAuthProvider` + `Store`) behind the MCP SDK's OAuth endpoints |
| `wilo/login.html` | Login page served at `/login`: Firebase Google sign-in (same as the tracker's `fe/auth.js`) |
| `schema/workout.schema.json` | The workout shape (JSON Schema 2020-12). Validated on every write |
| `config/wilo.json` | Project `wilo2-1ee44`, database `wilo`, Thom's uid, key **path** (`~/wilo-claude/service-account.json`, laptop only; `GOOGLE_APPLICATION_CREDENTIALS` overrides) |
| `pyproject.toml` | Package and dependencies (`firebase-admin`, `jsonschema`, `mcp`) |
| `docs/connector-sign-in.md` | Sign-in design (#38); `docs/principles.md`: the layers |

## Rules that must hold
- **Whose data is decided by code, never by Claude.** Every `data.py` function takes `uid` explicitly. Only two places choose it: the CLI's `main()` (config) and `current_uid()` in the server. **`uid` is never a tool argument.**
- **`current_uid()`:** with sign-in on (`AUTH = True`), it's the access token's `subject`; no token → `PermissionError`. **Never fall back to the config uid when `AUTH` is on.** With sign-in off (stdio, plain `--http`), it's the config uid.
- **Writes are dry runs by default.** `assign_workout` and `update_workout` (and the CLI's `assign` / `update`) write only with `write=True` / `--write`. The server instructions tell Claude to show Thom the dry run and write only after he approves.
- **Bind to `127.0.0.1` only** until the server sits behind HTTPS. There is no option to bind publicly, on purpose.
- **Secrets are never stored in plain text:** codes, tokens and pending sign-in IDs are stored only as sha256 hashes.

## Data model (decisions)
Schema = what a workout means to a human, not a contract with the tracker's internals (#28 discussion):
- Workout requires `id`, `name`, `exercises`. `assignedFor` = **the date the workout is for** (e.g. `"2026-10-08"`); `finishedAt` is set by the tracker's Finish.
- Exercise requires `name`, `sets`. Names are **free text**: no exercise catalog or IDs. Order = array order. Optional: `timed` (true → `reps` are seconds), `cue` (coach), `note` (Thom), `custom_name` (one free-text column per set: `Risers`, `Side` R/L, `Direction`, `Assistance`).
- Set requires `reps`, `done`. `lbs` and `reps` may be `""` (not set yet; blank doesn't mean bodyweight).
- Extra fields are allowed (the tracker writes `instanceId`, `exId`, `swapped`, …).
- `history` matches names **loosely but only cosmetically** (case, spacing, punctuation, plurals, word order). Synonyms (`crane-plane` vs `Basic cranes`) are for Claude to judge using `exercise_names`.

## Run it
```bash
.venv/bin/pip install -e .                                   # once; editable install
.venv/bin/python -m unittest discover tests -v               # 63 tests, no Firestore
.venv/bin/python -m wilo.data history bench                  # CLI (real data, read-only)
claude mcp add wilo -s local -- /home/thom/wilo/.venv/bin/python -m wilo.mcp_server   # stdio entry
.venv/bin/python -m wilo.mcp_server --http [--port N]         # HTTP, no sign-in (localhost)
.venv/bin/python -m wilo.mcp_server --http --auth [--port N]  # HTTP with sign-in (localhost)
```

## Sign-in (OAuth) in one picture
```
Claude ─▶ POST /mcp (no token) ─▶ 401 + WWW-Authenticate: Bearer resource_metadata=".../.well-known/oauth-protected-resource/mcp"
Claude ─▶ discovery docs ─▶ POST /register (DCR) ─▶ GET /authorize (PKCE S256, resource=…/mcp)
       ─▶ 302 to /login?request=… ─▶ Firebase Google popup ─▶ POST /login/callback {request, idToken}
       ─▶ Admin SDK verify_id_token → uid ─▶ auth code ─▶ redirect to Claude ─▶ POST /token ─▶ access + refresh
Claude ─▶ POST /mcp (Bearer) ─▶ tools run with current_uid() = token.subject
```
- **The MCP SDK v2 provides** the metadata, `/register`, `/authorize`, `/token`, PKCE verification, client auth and exact redirect matching. **We provide** `WiloAuthProvider` (storage + the login step) and the two `/login` routes.
- **Storage:** Firestore `oauth_clients`, `oauth_pending` (10 min), `oauth_codes` (5 min, single use), `oauth_access` (1 h), `oauth_refresh` (30 days, **rotated** on each use). Keys are sha256 hashes. All docs carry `expires_at`. Each access/refresh doc records its partner's hash (`pair`): **revoking either one revokes both** (RFC 7009). Nothing in the Firestore rules allows `oauth_*`, so browsers can't read them.
- **Redirect checks:** the SDK requires an exact registered match at `/authorize`; `WiloAuthProvider.authorize()` checks again (defense in depth).
- **Redirects allowed at registration:** `https://claude.ai/api/mcp/auth_callback` (hosted Claude apps) and `http://localhost|127.0.0.1:<any port>` (Claude Code).
- **Audience check:** `validate_token_resource=True`, so `/mcp` refuses tokens issued for another resource. If a client sends no `resource`, the provider records this server's `/mcp` URL.
- **Login page safety:** it renders only for a known, unexpired pending ID matching `[A-Za-z0-9_-]{20,}`. Anything else → 400, nothing echoed. It shows the host the user is about to be sent back to.
- **DCR, not CIMD:** the SDK doesn't advertise CIMD (`client_id_metadata_document_supported`, `"none"` auth method), so Claude falls back to DCR. Fine at this scale.
- **Shared identity with the tracker:** same Firebase project and Google provider, so the same uid. Sessions are separate: tracker = Firebase ID token in the browser with rules on Firestore; connector = our OAuth tokens with `current_uid()` on the server (admin SDK).

## Verified end to end (2026-10-08)
Real Claude Code, real browser, real Google sign-in against `--http --auth` on `localhost:8077`. Log sequence: discovery 200 → `/register` 201 (loopback `localhost:50175`) → `/authorize` 302 (S256, `resource` sent) → `/login` 200 → `/login/callback` 200 (real Firebase token verified) → `/token` 200 → authenticated `/mcp` 200s. Firestore: the access and refresh tokens have `subject` = Thom's uid and `resource` = `http://localhost:8077/mcp`; pending and code docs were consumed.

## Tests (`tests/`)
| File | Covers |
|---|---|
| `test_wilo_data.py` | Schema (3), assign (5), name matching (2), history/names (3), update (3), two-user isolation (3). Also the **fake db** (`FakeDB`, `Ref`, `Snap`) the other tests reuse |
| `test_mcp_server.py` | The 8 tools through the MCP layer (9): no tool takes a uid, dry-run defaults, per-user reads and writes |
| `test_auth.py` | The provider (19): full flow, single use, expiry, client binding, rotation, revoke (pairs), hashing, default resource, unregistered redirect |
| `test_signin_http.py` | The OAuth flow over HTTP in-process with `TestClient` (15, incl. `/revoke` and unregistered redirect), plus `main()` really switching sign-in on (1) |

Practice: after adding a guard, **break it on purpose and check a test fails**, then restore it (done for dry-run defaults, `current_uid()`, the `global` in `main()` and `validate_token_resource`).

## Gotchas we hit
- **MCP Python SDK v2 ≠ v1:** the class is `MCPServer` (`mcp.server.mcpserver`), not `fastmcp`; results use `is_error` / `structured_content`; `server.call_tool` **raises** `ToolError` on bad arguments; `get_access_token()` (`mcp.server.auth.middleware.auth_context`) gives the request's token. **Check the installed package before assuming an API.**
- **`global AUTH, server` in `main()`:** without it, `--auth` creates locals and tools silently use the config uid. Guarded by `test_main_with_auth_turns_sign_in_on`.
- **`TestClient` must be entered** (`TestClient(app).__enter__()` or `with`), otherwise the MCP session manager isn't started ("Task group is not initialized").
- **Mocking `MCPServer.run`** needs `autospec=True` to receive `self`.
- **SDK `/revoke` quirk:** `RevocationRequest.client_secret` is `str | None` with no default, so the field must be present: public clients (Claude, no secret) get `400 client_secret: Field required` unless they send `client_secret=` empty. Reported upstream: [python-sdk #3508](https://github.com/modelcontextprotocol/python-sdk/issues/3508) (open as of 2026-10-08); once fixed, drop the empty `client_secret` in `test_revoke_endpoint_kills_the_whole_pair`. Revocation logic itself is ours (`revoke_token`: either token of a pair revokes both).
- **The editable install runs whatever branch is checked out.** Claude Code's `wilo` breaks on a branch without `wilo/`.
- **A running Claude Code session only loads MCP servers at startup.** After `claude mcp add`, use a new session (`cd ~/wilo && claude`) to see the new server.
- **Ports:** an old test server can hold a port (`ss -ltnp | grep :8000`). Use another `--port`; the issuer follows the port.
- **Don't name a folder after a dependency:** the old `mcp/` folder shadowed the `mcp` SDK. That's why everything lives in `wilo/`.
- **Stacked PRs:** retarget the next PR to `main` right after its base merges, or it merges into the old branch (#37 had to be re-landed as #42).
- **Tracker quirks (#29):** the tracker ignores `timed` (it reads `target.duration_sec`), and Load opens the **newest** `assignedFor`, so post one workout at a time until #29 is done.

## What's next
- **Hosting (needs Blaze):** Cloud Run in `wilo2-1ee44` with its own service account (no JSON key on the server). Idea: Firebase Hosting rewrites, so it lives on `wilo2-1ee44.web.app` (already a Firebase authorized domain). Then add it in claude.ai → Customize → Connectors with `https://…/mcp`.
- **Before anyone else connects:** lock the open top-level Firestore collections (#15 step 4).
- **Instructions out of code (#40):** move `INSTRUCTIONS` and the tool docstrings (which Claude reads as tool descriptions) into one file.
- Open questions: scopes (one `workouts` for now), token lifetimes, a "connected to Claude" control in the tracker to revoke access.

## Where the history is
#32, #34 data engine (closed #19) · #35 MCP server + `wilo` package · #36 per-user uid · #37 → #42 tool tests + HTTP · #38 principles + sign-in design · #39 sign-in · issues #31 (build plan + Claude connector research), #40, #29, #30, #15, #14.
