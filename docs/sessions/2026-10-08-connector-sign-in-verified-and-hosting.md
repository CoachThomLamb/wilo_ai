# 2026-10-08 (Thu): connector sign-in verified for real, review fixes, made hostable

Previous: `2026-10-07-script-test.md`. Working guide for this code: `docs/mcp-server-and-connector-guide.md`.

## Where it stopped
- **PR #44 is open** (`--public-url`, credentials fallback, `Dockerfile`). Thom reviews and merges it **before** any deploy: don't deploy from a working branch.
- **Blaze is on** for `wilo2-1ee44` (Thom, 2026-10-08). **Ask:** is a budget alert set ($1–5)? Recommended, since Blaze has a card on file.
- **`gcloud` isn't installed** on the laptop. Docker and the Firebase CLI are.
- Everything is shut down: no test servers or containers running, only the normal `wilo` MCP entry, `oauth_*` collections empty, repo on `main`. The `wilo-connector` Docker image is built locally (harmless; `docker build` again anyway).
- **Today's workout** (`chest-biceps-oct-8`, lunch): whether Thom trained and how it went wasn't discussed. Ask, and if done, review it with `wilo` and plan the next one.

## Tomorrow: step 3 (deploy), then 4–5
1. **Merge #44.**
2. **Install `gcloud`** (Arch: the `google-cloud-cli` package from the AUR, or Google's installer). Then `gcloud auth login` and `gcloud config set project wilo2-1ee44`.
3. **Pick the public address first.** It sets `PUBLIC_URL`:
   - **A. Firebase Hosting rewrite** → `https://wilo2-1ee44.web.app` (known in advance, already a Firebase sign-in domain). Needs `firebase.json` rewrites for `/mcp`, `/.well-known/**`, `/authorize`, `/token`, `/register`, `/revoke`, `/login**`. **It touches the tracker's hosting config, so review it carefully.** To verify: that Hosting forwards these paths (and the `401`'s `WWW-Authenticate` header) correctly.
   - **B. The bare `*.run.app` URL** → deploy once, read the URL, set `PUBLIC_URL`, and add that domain to Firebase Auth's authorized domains (console).
   - Lean: **B first** (fewer moving parts, proves the deploy), then A if a nicer URL or one-tap sign-in matters.
4. **Region:** match Firestore's location (`gcloud firestore databases describe --database=wilo`).
5. **Service account:** a dedicated one with `roles/datastore.user` is better than the default compute account.
6. **Deploy** (commands in the guide): `gcloud run deploy wilo-connector --source . --region … --allow-unauthenticated --set-env-vars PUBLIC_URL=…`.
7. **Check at the public URL:** `POST /mcp` → `401` with `resource_metadata` on the public host; both discovery docs.
8. **Step 5:** claude.ai → Customize → Connectors → Add custom connector → `https://…/mcp` → Connect → Google sign-in. Then ask from the **phone app**, and also try revoking (disconnect).

## Done today
- **Real end-to-end sign-in with Claude Code**, twice: register → authorize (PKCE, `resource` sent) → our Firebase login page → `/token` → authenticated tool calls. The token's `subject` was Thom's uid. A fresh session answered "next workout" correctly via `wilo-auth`.
- **Review of #39 found 2 issues:**
  1. Revocation didn't revoke the token's partner. **Real bug; fixed** (each access/refresh doc records its `pair`; revoking either revokes both).
  2. Redirect URI not checked in the provider. **The SDK already enforces it** at `/authorize` (proven by a test); added the provider check as defense in depth.
- **Live re-test found an SDK bug:** Claude Code's "Clear authentication" calls `/revoke` without a `client_secret`, and MCP SDK v2 rejects that ([python-sdk #3508](https://github.com/modelcontextprotocol/python-sdk/issues/3508), already reported upstream; Thom added a 👍). **Local workaround** in `wilo/auth.py`; re-verified live (`/revoke` 200 ×2, both tokens gone).
- **Token audience check** (`validate_token_resource=True`) after Thom spotted the SDK warning.
- **#39 merged:** sign-in, the guide, review fixes. Stacked-PR lesson recorded (#37 → #42).
- **#44 (open):** `--public-url` (only with sign-in, https, non-empty), credentials fall back to Cloud Run's identity, `Dockerfile` with an allowlist `.dockerignore`. Running the container caught a bug (an empty `PUBLIC_URL` silently fell back to localhost mode), now fixed. 70 tests.

## Decisions and why
- **#29 (tracker reads `timed`) deferred:** Thom: "small potatoes". The connector comes first.
- **Projected cost: $0/month** at Thom's usage (Cloud Run scales to zero; Firestore/Auth/Hosting free tiers). A cold start of a few seconds is accepted rather than paying for an always-on instance.
- **Never expose the server without sign-in:** `--public-url` requires `--auth`. The SDK's DNS-rebinding protection is left at its default (localhost only), since every public tool call needs a token.
- **Docs get descriptive names** (Thom rejected a nested `CLAUDE.md`); the root `CLAUDE.md` has a one-line pointer to the guide.

## Outside the repo
- Blaze on `wilo2-1ee44` (pay-as-you-go, card on file).
- Key: `~/wilo-claude/service-account.json` (used locally; **not** in the image; Cloud Run will use its own identity). A duplicate copy is at `~/.config/wilo/service-account.json`, unused.
- Backups: `data/backup-2026-10-05/`, `data/backup-2026-10-07/` (local only).

## Open PRs and issues
- PR #44: make the connector hostable (closes #43).
- #31: connector build plan (steps 3–5 left). #40: instructions out of code. #29: tracker `timed` (deferred). #30: remove the swap feature. #15: lock rules before others connect. #14: multi-user connector.
- Parked: #25 coaching loop, #28 full schema.
