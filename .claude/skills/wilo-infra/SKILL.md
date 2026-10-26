---
name: wilo-infra
description: Maintain WILO's infrastructure - Firebase Hosting, Firestore (rules, data upkeep), Firebase Auth, the Render connector, GitHub Actions, service account keys, backups. Use when deploying, checking that a merge went live, changing rules or auth domains, cleaning up data, rotating keys, or answering "what runs where".
---

# WILO infrastructure

The map of what runs where is `docs/infrastructure-and-rebuild.md`. **Read it first**; this skill is only the
runbook around it. Connector code details: `docs/mcp-server-and-connector-guide.md`.

## Rules
- **Ask before anything live.** Deploys, rules releases, Firestore writes or deletes, console changes, key
  changes and live checks (curl, `gcloud`, `firebase`, Firestore reads) all need Thom's OK. Name the
  command and why, then run it.
- **One path to the data:** the wilo connector (#87). Not the local stdio server, not `firebase_admin`
  scripts. Cleanup the connector can't do (deletes) is done by Thom in the Firebase console.
- **Never deploy from a branch or uncommitted state.** Merging to `main` deploys Hosting (GitHub Action)
  and the connector (Render).
- **Keys:** never print, commit or copy them. Render gets the `wilo-connector` key, never the admin key.
- **Keep the doc true:** when a piece changes, update `docs/infrastructure-and-rebuild.md` in the same PR,
  including its "State as of" line and the gaps table (§7).

## Common tasks

**Did a merge go live?**
- Hosting: `gh run list --workflow firebase-hosting-merge.yml -L 3` (should be `success`).
- Connector: Render dashboard → `wilo-connector` → Events (Thom). It sleeps after 15 min; the first call
  takes ~1 min.
- Phone: a home-screen app resumes its old page. Swipe it away and reopen. The tracker's version label is
  hand-set (`fe/index.html`), so it doesn't prove which merge is live.

**Run the tests** (no Firestore needed): `.venv/bin/python -m unittest discover tests`. CI doesn't run
them (#46), so run them before every merge.

**Change Firestore rules:** edit `firestore.rules`, PR, merge, then deploy by hand (CI deploys Hosting
only, #50): `firebase deploy --only firestore:rules`. Check the release on the `wilo` database in the
console. Update the "last release" date in the doc.

**PR previews** all deploy to one fixed channel, `dev` (#115): the PR comment shows its URL, and the last PR
pushed is what it serves. **Can't sign in** (`Error 400: redirect_uri_mismatch`) means the dev host changed (the
channel expired after 30 days without a PR): Thom adds `https://<dev host>/__/auth/handler` (and the origin) to the
OAuth web client in Google Cloud → APIs & Services → Credentials (doc §6 step 2).

**Connector checks** (with OK):
```bash
curl -i -X POST https://wilo-connector.onrender.com/mcp -d '{}'                    # expect 401
curl https://wilo-connector.onrender.com/.well-known/oauth-authorization-server    # endpoints on the same host
```
Env vars and the secret file live only in the Render dashboard (no `render.yaml`, #50).

**Data upkeep** (#53): stray completed copies, stale `assigned` plans, legacy top-level collections.
Find them with the connector's read tools, list the doc IDs for Thom, and he deletes them in the console.
A test Finish marks a workout done: deleting its completed copy (or setting `inProgress: true`) brings it
back in the tracker.

**Backups** (#49): none automated (Spark plan, no PITR). The only copies are hand-made dumps in
`~/wilo/data/backup-*` on the laptop, and there's no restore script. Before any risky data change,
suggest a fresh dump first.

**Keys and access** (#51): see the service account table in doc §4. Rotation and the duplicate admin key
are open work.

## Before you finish
- Doc updated if anything moved; open gaps still match §7.
- The session note says what changed outside the repo (console, Render, keys).
