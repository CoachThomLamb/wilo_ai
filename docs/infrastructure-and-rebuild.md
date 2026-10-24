# WILO infrastructure: how it works and how to rebuild it

**For:** Thom, the team, and future Claude sessions. It also serves as the outline for a talk.
**State as of:** 2026-10-21, checked against the code on `main`, GitHub and the session notes. The live systems (Firebase, GCP, Render, claude.ai) were last checked directly on 2026-10-09; the rules release on 2026-10-12.
**Keep it current:** when a piece moves, update this file in the same PR.

Contents: [1. One minute](#1-the-one-minute-version) · [2. The pieces](#2-the-pieces) · [3. A workout's journey](#3-a-workouts-journey) · [4. Security](#4-security-model) · [5. Deep dive](#5-deep-dive-per-component) · [6. Rebuild](#6-rebuild-from-scratch-checklist) · [7. Gaps](#7-gaps-what-we-cant-recover-today) · [8. If we did it again](#8-if-we-built-it-again)

---

## 1. The one-minute version

WILO is a workout coach in three parts:
1. **You talk to Claude** (phone app, web, or Claude Code on the laptop). Claude plans your next workout.
2. **Claude saves the plan through a small server we wrote** (the *connector*) into a **Firestore database**.
3. **At the gym, the tracker web page** loads the plan, you log sets, and Finish saves what you actually did. Next time you talk to Claude, it reads that and adjusts.

Everything is tied to your **Google sign-in**, so each person only sees their own workouts.

```mermaid
flowchart LR
    U(("You"))
    subgraph Claude["Claude (Anthropic)"]
        APP["Claude app<br/>phone / web"]
        CC["Claude Code<br/>laptop"]
    end
    subgraph Render["Render (free tier)"]
        CONN["Connector<br/>wilo/mcp_server.py<br/>+ sign-in"]
    end
    subgraph Google["Google Firebase project wilo2-1ee44"]
        AUTH["Firebase Auth<br/>Google sign-in"]
        FS[("Firestore<br/>database: wilo")]
        HOST["Firebase Hosting<br/>tracker web page"]
    end
    GH["GitHub<br/>wilo_ai repo"]

    U -- "plan my workout" --> APP
    U -- "at the gym" --> HOST
    APP -- "tools over HTTPS" --> CONN
    CC -- "same tools over HTTPS (#87)" --> CONN
    CONN -- "read / write" --> FS
    CONN -. "verify who you are" .-> AUTH
    HOST -- "load plan / save log" --> FS
    HOST -. "sign in" .-> AUTH
    GH -- "deploys on merge" --> HOST
    GH -- "deploys on merge" --> CONN
```

**Talk version (5 lines):** chat → plan → database → tracker → log → chat. The AI never touches the database directly: it calls 15 small tools (workouts, the coaching method and profile, todos), and our code decides whose data they touch. Writes are dry runs until you say yes. It costs $0/month today. All code is in one GitHub repo, and merging to `main` deploys it.

---

## 2. The pieces

| Piece | What it is | Where it lives | Config is in | Deploys how | Cost |
|---|---|---|---|---|---|
| **Repo** `CoachThomLamb/wilo_ai` | All code, docs, rules | GitHub (**public**) | `main` | — | $0 |
| **Tracker** `fe/index.html` (+ `today.html`, `auth.js`) | Plain HTML pages: the tracker (Load the next unfinished workout, log sets, Finish) and the Today page (todos). Sign-in required | Firebase Hosting `https://wilo2-1ee44.web.app` | `firebase.json` | GitHub Action on merge to `main`; preview per PR | $0 (Spark) |
| **Firestore** database `wilo` | All workout data, todos, coach profiles + sign-in tokens | GCP `northamerica-northeast2` (Toronto) | `firestore.rules`, `config/wilo.json` | Rules: **manually** with `firebase deploy --only firestore:rules` (last 2026-10-12) | $0 (free quota) |
| **Firebase Auth** | Google sign-in, one uid per person | Firebase project `wilo2-1ee44` | Console only (provider: Google; authorized domains) | Console | $0 |
| **Data engine** `wilo/data.py` | All Firestore logic + CLI | Repo (runs wherever it's imported) | `config/wilo.json`, `schema/workout.schema.json` | With the connector | — |
| **Connector** `wilo/mcp_server.py` + `wilo/auth.py` + `wilo/login.html` + `wilo/chat.py` | MCP server: 15 tools + OAuth sign-in, plus `/chat`: the tracker's coach chat (Claude API over the same tools) | Render web service `wilo-connector` → `https://wilo-connector.onrender.com/mcp` | `Dockerfile`; env + secret file **in the Render dashboard** | Render auto-deploys every commit to `main` | $0 (sleeps after 15 min) |
| **Local MCP server** | Same tools over stdio, for Claude Code. **Being removed (#87):** sessions reach the data through the connector, like a user. The stdio mode stays in the code for tests | Laptop: `.venv`, editable install | `~/.claude.json` (`claude mcp add wilo …`) | Runs the checked-out branch | $0 |
| **claude.ai connector** | "wilo" custom connector (DCR + sign-in) | Each user's claude.ai account | claude.ai → Settings → Connectors | Manual, once per user | Claude plan |
| **Coach** `wilo/coach.md` + per-user profile | The coaching method (any user), served by the `coaching_method` tool; what's personal is data at `users/{uid}/coach/profile` (`get_profile` / `update_profile`) | Repo + Firestore | `wilo/coach.md` | With the connector | — |
| **Service accounts** (GCP) | Machine identities with keys | GCP IAM | See [§4](#4-security-model) | `gcloud` / console | $0 |
| **Laptop** | Keys, venv, local backups | `~/wilo`, `~/wilo-claude/`, `~/wilo/data/` | — | — | — |

**Accounts that own things:** GitHub `CoachThomLamb`; Google `thomlamb74@gmail.com` (the only **owner** of the GCP/Firebase project); Render (signed in with GitHub); claude.ai. **Billing:** none. The project has no active billing account (Spark plan), so Cloud Run, scheduled backups and anything else that needs Blaze are unavailable.

---

## 3. A workout's journey

```mermaid
sequenceDiagram
    actor T as Thom
    participant C as Claude (app)
    participant S as Connector (Render)
    participant F as Firestore (users/uid/...)
    participant W as Tracker (web)

    T->>C: "Plan today's pull day"
    C->>S: coaching_method, get_profile, recent_completed, exercise_history
    S->>F: read completed workouts
    F-->>S: history
    S-->>C: JSON
    C->>S: assign_workout(plan)  [dry run]
    S-->>C: what would be written
    C-->>T: shows the plan
    T->>C: "post"
    C->>S: assign_workout(plan, write=True)
    S->>F: write users/uid/assigned/doc
    Note over T,W: at the gym
    T->>W: Load
    W->>F: next assigned (earliest by assignedFor, not yet completed)
    T->>W: log sets, Finish
    W->>F: write users/uid/completed
    Note over C,F: next chat: Claude reads completed, reviews, plans again
```

**Data layout (Firestore database `wilo`):**

| Path | What | Written by |
|---|---|---|
| `users/{uid}/assigned/{docId}` | Planned workouts (`assignedFor` = the day) | Connector / CLI |
| `users/{uid}/completed/{docId}` | Finished workouts (`finishedAt`) | Tracker Finish |
| `users/{uid}/todos/{docId}` | Todos for the Today page | Connector, Today page |
| `users/{uid}/coach/profile` | Coaching profile: `preferences`, `limitations`, `plan`, `notes` (free text) | Connector (`update_profile`) |
| `oauth_clients`, `oauth_pending`, `oauth_codes`, `oauth_access`, `oauth_refresh` | Connector sign-in state, sha256-hashed | Connector |
| `assigned`, `completed`, `programs`, `sessions` (top level) | **Legacy, unused.** Locked since 2026-10-12: the rules deny all browser access (#15, #69). Still to delete (#53) | Nothing |

---

## 4. Security model

**Who can touch what:**

```mermaid
flowchart TB
    subgraph Internet
        B["Any browser<br/>(Firebase config is public)"]
        CL["Claude servers"]
    end
    subgraph Rules["Firestore security rules (apply to browsers)"]
        R1["users/{uid}/**<br/>only that signed-in user"]
        R2["everything else: legacy top-level<br/>collections, oauth_*<br/>DENIED (since 2026-10-12)"]
    end
    subgraph Admin["Service accounts (bypass the rules)"]
        K1["firebase-adminsdk<br/>Auth admin + token creator<br/>key: laptop only"]
        K2["wilo-connector<br/>datastore.user only<br/>key: Render secret file"]
        K3["github-action-…<br/>Hosting + Auth admin + more<br/>key: GitHub secret"]
    end
    B --> R1
    B --> R2
    CL -- "OAuth token" --> CONN["Connector: uid = token subject"]
    CONN --> K2
```

- **Browsers** go through the Firestore rules. `users/{uid}/**` is locked to that user; everything else is denied (#15, rules deployed 2026-10-12). The rules check only the owner, not the fields, so the schema is enforced by the connector (on its writes), not by the rules.
- **The connector** decides whose data a call touches from the OAuth token (`current_uid()`). The uid is never a tool argument. It refuses to listen publicly without sign-in (`--public-url` requires `--auth` and https).
- **Service accounts bypass the rules**, so their keys are the crown jewels:

| Service account | Roles | Key lives | Used by |
|---|---|---|---|
| `firebase-adminsdk-fbsvc@…` | `firebaseauth.admin`, `iam.serviceAccountTokenCreator`, `firebase.sdkAdminServiceAgent` | `~/wilo-claude/service-account.json` (**plus an unused copy** at `~/.config/wilo/service-account.json`) | Local CLI + local MCP server |
| `wilo-connector@…` (2026-10-09) | `datastore.user` only | Render secret file `wilo-connector-key.json`; local copy `~/wilo-claude/wilo-connector-key.json` | The hosted connector |
| `github-action-1362674060@…` | `firebasehosting.admin`, `firebaseauth.admin`, `cloudfunctions.developer`, `run.viewer`, `serviceusage.*` | GitHub secret `FIREBASE_SERVICE_ACCOUNT_WILO2_1EE44` | Hosting deploys (created by `firebase init hosting:github`) |

- **Not secrets (public by design):** the Firebase web config (`apiKey` etc. in `fe/index.html`, `wilo/login.html`), Thom's uid in `config/wilo.json`. They identify the project but don't grant access. The rules and the server do that.
- **Firebase Auth authorized domains:** `localhost`, `wilo2-1ee44.firebaseapp.com`, `wilo2-1ee44.web.app`, `wilo-connector.onrender.com`, plus one `wilo2-1ee44--prNN-….web.app` per PR preview (added automatically, low risk, clutter).

---

## 5. Deep dive per component

The code-level guide for the connector is [`mcp-server-and-connector-guide.md`](mcp-server-and-connector-guide.md) (rules, OAuth flow, tests, gotchas). The sign-in design is [`connector-sign-in.md`](connector-sign-in.md), the layering is [`principles.md`](principles.md). This section covers what those don't: the infrastructure around the code.

### 5.1 GitHub
- Repo `CoachThomLamb/wilo_ai`, **public**, default branch `main`. Work happens on branches with PRs, and merging to `main` deploys (Hosting via Actions, connector via Render).
- **Actions:** `firebase-hosting-pull-request.yml` (preview channel per PR, expires after 7 days), `firebase-hosting-merge.yml` (live deploy on push to `main`). **No tests run in CI** (#46).
- **Secret:** `FIREBASE_SERVICE_ACCOUNT_WILO2_1EE44` (the github-action key, created 2026-09-25).
- Gitignored on purpose: `data/` (local Firestore dumps), `.claude/skills/`, `.agents/`, `.env`.

### 5.2 Firebase project `wilo2-1ee44`
- Project number `103580826325`. One web app "Wilo" (`1:103580826325:web:0e5cc800c5cbb29691c05c`). Plan: **Spark** (no billing).
- **Hosting:** site `wilo2-1ee44` serves `fe/`. `firebase.json` sets `Cache-Control: no-cache` on HTML/JS so phones get new versions.
- **Firestore:** named database **`wilo`** (not `(default)`, so every client must name it), Native mode, `northamerica-northeast2`. **Point-in-time recovery: off. Delete protection: off. Backup schedules: none.**
- **Rules:** `firestore.rules`, deployed **by hand** (CI deploys Hosting only, #50). Last release 2026-10-12 (#69, the lock); checked then that the `wilo` database's release updated.
- **Auth:** Google provider only.
- Thom's Google account also has ~26 other Firebase projects (e.g. an older `wiloworkout-85481`). Only `wilo2-1ee44` is live.

### 5.3 Connector on Render
- Service `wilo-connector`: repo `wilo_ai`, branch `main`, Docker (`Dockerfile` at the root), Free instance, region Virginia, auto-deploy on every commit to `main`.
- Env: `PUBLIC_URL=https://wilo-connector.onrender.com`, `GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/wilo-connector-key.json`. Render sets `$PORT`.
- Env for the coach chat (`/chat`, `wilo/chat.py`): `ANTHROPIC_API_KEY` (secret: our Claude API key; without it `/chat` answers 502 and the rest of the server is unaffected). Optional: `WILO_CHAT_MODEL` (default `claude-opus-5-5`), `WILO_CHAT_EFFORT` (default `medium`), `WILO_CHAT_UIDS` (who may chat; default the uid in `config/wilo.json`), `WILO_CHAT_DAILY_LIMIT` (default 100 messages per user per day), `WILO_TZ` (default `America/Toronto`). Every model call logs one `chat:` line to the Render log: model, stop reason, and tokens as `in` (uncached), `read` (cache hits, 0.05× input price on Opus 5.5), `write` (cache writes: 2× for the 1-hour fixed prefix, 1.25× for the 5-minute chat) and `out`. Total input = in + read + write.
- Secret file: `wilo-connector-key.json` (the `wilo-connector` key).
- **All of this lives only in the Render dashboard.** There's no `render.yaml`.
- Sleeps after 15 min idle. The first request takes ~1 min.
- Why Render: Google billing rejected the prepaid card, so Cloud Run wasn't possible. Details and the Cloud Run alternative are in the connector guide.

### 5.4 Python package `wilo/`
- `pyproject.toml`: Python ≥ 3.12; dependencies `firebase-admin`, `jsonschema`, `mcp` are **unpinned**. **The code needs MCP SDK v2** (`MCPServer`). Working versions on 2026-10-09: Python 3.14.7, `mcp` 2.3.0, `firebase-admin` 7.7.0, `google-cloud-firestore` 2.31.0, `jsonschema` 4.26.0, `starlette` 1.7.0, `uvicorn` 0.54.0, `pydantic` 2.13.5.
- Docker base image `python:3.14-slim` (a tag, not a digest).
- 100 tests, all with fakes, no Firestore or API key needed: `.venv/bin/python -m unittest discover tests`. `anthropic` is a dependency since the coach chat (2.2.0 on 2026-10-23).

### 5.5 Claude side
- **claude.ai:** custom connector "wilo" → `https://wilo-connector.onrender.com/mcp`, Sign in now + Register automatically (DCR). Read tools always allowed; `assign_workout` / `update_workout` need approval. Works on web and phone.
- **Claude Code (laptop):** reaches the data through the same claude.ai connector (#87: one path to the data, like a user). The old local entry `claude mcp add wilo -s local -- /home/thom/wilo/.venv/bin/python -m wilo.mcp_server` (stdio, admin key, Thom's uid from `config/wilo.json`) is being removed.
- **Instructions Claude reads (coaching):** `wilo/coach.md` through the `coaching_method` tool, the user's profile through `get_profile`, and the tool descriptions in `wilo/mcp_server.py`. claude.ai doesn't show the server's `INSTRUCTIONS` string to the model, which is why the method sits behind a tool (#48).
- **Instructions for coding sessions:** `CLAUDE.md`, which loads `.claude/instructions.md` and `.claude/memory.md` (#88 proposes `docs/principles.md` in place of `memory.md`).
- **Old coach skill `wilo-workout-coach`** (claude.ai only): superseded by `wilo/coach.md` (#48). It describes the old `sessions`/`programs` collections and a script that's gone; remove it from claude.ai so it can't contradict the method.

### 5.6 The laptop
- `~/wilo` (repo + `.venv`), `~/wilo-claude/service-account.json` (admin key), `~/wilo-claude/wilo-connector-key.json` (connector key), `~/.config/wilo/service-account.json` (unused duplicate admin key).
- **The only Firestore backups:** `~/wilo/data/backup-2026-10-05/`, `backup-2026-10-07/` and `backup-2026-10-10/` (one JSON file per collection, made by hand; the last one before the rules lock).
- Tools: `gh`, `docker`, `firebase` (15.29.0), `gcloud` (585, `google-cloud-cli-lite` from the AUR; on PATH in new login shells, else `/opt/google-cloud-cli/bin/gcloud`).

---

## 6. Rebuild from scratch (checklist)

Ordered so that each step only depends on earlier ones. Secrets are **generated**, never copied from this doc. Not yet tested end to end; that's a separate task.

**0. Accounts and tools**
- [ ] Accounts: GitHub (`CoachThomLamb`), Google (owner of the Firebase project), Render (sign in with GitHub), claude.ai.
- [ ] Tools: `git`, Python ≥ 3.12, `docker`, `gh`, Firebase CLI (`npm i -g firebase-tools`), `gcloud` (Omarchy: `omarchy pkg aur add google-cloud-cli`).

**1. Code**
- [ ] `git clone https://github.com/CoachThomLamb/wilo_ai.git ~/wilo && cd ~/wilo`
- [ ] `python -m venv .venv && .venv/bin/pip install -e .`. If `mcp` resolves to anything but 2.x, pin `mcp>=2,<3` (see §5.4).
- [ ] `.venv/bin/python -m unittest discover tests` → 100 OK.

**2. Firebase project** (skip if `wilo2-1ee44` still exists)
- [ ] Create the project. Add a **web app** and copy its config into the `initializeApp({...})` blocks in `fe/index.html` and `wilo/login.html`.
- [ ] Firestore: create the **named database `wilo`** in `northamerica-northeast2`, Native mode. Turn on **delete protection**.
- [ ] Auth: enable the **Google** provider.
- [ ] **OAuth redirect URIs** (Google Cloud console → APIs & Services → Credentials → the web client Firebase uses, "Web client (auto created by Google Service)"): add `https://<project>.web.app/__/auth/handler`. The tracker signs in through its own domain (`authDomain` = the page's host, needed for in-app browsers), so **every domain the tracker runs on needs its handler URI here**, PR previews included. A missing one gives `Error 400: redirect_uri_mismatch`.
- [ ] Update `.firebaserc` and `config/wilo.json` (`project`).
- [ ] `firebase deploy --only firestore:rules` and `firebase deploy --only hosting`.
- [ ] `firebase init hosting:github`. It recreates the github-action service account and the `FIREBASE_SERVICE_ACCOUNT_…` secret. Fix the secret name in both workflow files if the project ID changed.

**3. Service accounts and keys**
- [ ] Admin key for the laptop: Firebase console → Project settings → Service accounts → Generate new private key → `~/wilo-claude/service-account.json` (`chmod 600`).
- [ ] Connector account:
  ```bash
  gcloud config set project <project>
  gcloud iam service-accounts create wilo-connector --display-name="WILO connector (Render)"
  gcloud projects add-iam-policy-binding <project> \
    --member="serviceAccount:wilo-connector@<project>.iam.gserviceaccount.com" --role="roles/datastore.user" --condition=None
  gcloud iam service-accounts keys create ~/wilo-claude/wilo-connector-key.json \
    --iam-account=wilo-connector@<project>.iam.gserviceaccount.com
  ```
  A new grant can take a minute (`403` until then).

**4. Data**
- [ ] Sign in to the tracker once with Google, so your **new uid** exists. **A new Firebase project means new uids**, so data must go under the new `users/{uid}`.
- [ ] Put the new uid in `config/wilo.json`.
- [ ] Restore from the newest `data/backup-*/users__<old uid>__*.json` into `users/<new uid>/…`. **There's no restore script yet** (gap). Write a one-off with `wilo.data.connect()`: dry run first, then write.

**5. Local Claude Code**
- [ ] Nothing extra: after step 7, Claude Code uses the same claude.ai connector (#87). In a new session, ask "what did I do last workout?".

**6. Connector on Render**
- [ ] New → Web Service → repo `wilo_ai`, branch `main`, runtime Docker, instance Free, name **`wilo-connector`**. The URL follows the name, so check it.
- [ ] Env: `PUBLIC_URL=https://<name>.onrender.com`, `GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/wilo-connector-key.json`. Secret file `wilo-connector-key.json` = contents of the **connector** key (**never the admin key**). For the coach chat, `ANTHROPIC_API_KEY` too (§5.3). Health check path: empty.
- [ ] Firebase Auth → Authorized domains → add `<name>.onrender.com`.
- [ ] Check:
  ```bash
  curl -i -X POST https://<name>.onrender.com/mcp -d '{}'                    # 401, resource_metadata on the same host
  curl https://<name>.onrender.com/.well-known/oauth-authorization-server    # every endpoint on the same host
  ```

**7. Claude**
- [ ] claude.ai → Settings → Connectors → Add custom connector → `https://<name>.onrender.com/mcp` → Sign in now + Register automatically → Connect → Google sign-in → 15 tools.
- [ ] Coach: nothing to upload. The method is `wilo/coach.md` (served by the connector); each user's profile starts empty and fills in through `update_profile`.

**8. End-to-end check**
- [ ] On the phone: ask Claude for your last workout, plan one, approve the write → tracker → Load shows it → Finish → Claude sees it.

---

## 7. Gaps: what we can't recover today

**Open**

| # | Gap | Risk | Issue |
|---|---|---|---|
| 1 | **No Firestore backups**: PITR off, delete protection off, no schedule (needs billing). The only copies are three hand-made dumps on the laptop (last 2026-10-10). No restore script | One bad write or deletion loses training history for good, now for more than one user | #49 |
| 2 | **Infrastructure isn't in code**: Render settings exist only in its dashboard, deps are unpinned (MCP v2 is required), the base image is a moving tag, rules are deployed by hand | A rebuild may produce something different, or break on a new SDK | #50 |
| 3 | **Keys and access**: a duplicate admin key on the laptop; the github-action account has broad roles; no rotation; one human owner everywhere; the Firebase browser key isn't restricted by referrer | A lost laptop or account locks out the project; a leaked key does a lot of damage | #51 |
| 4 | **Data upkeep**: legacy top-level collections still hold data (locked, unused); re-finishing a workout leaves stray completed copies and moves `finishedAt`; stale plans pile up in `assigned`; **no delete through the connector**, so cleanup needs the Firebase console | Wrong "next workout", messy history, cleanup outside the one path to the data | #53 |
| 5 | **Stale docs**: README (dev mode, `tracker.html`), `data/README.md`, `migrate_firestore.py`, older design docs in `docs/` | Confusing for a new person or LLM | #53 |
| 6 | **No tests in CI** | Broken code can merge and auto-deploy to Render | #46 |
| 7 | **No billing account**: Cloud Run, backups and Blaze features are unavailable; the old budget sits on a closed credit account | Limits options; no alert if billing comes back | Part of #49 / #51 |

**Closed since 2026-10-09**

| Gap | How | Issue |
|---|---|---|
| The coach skill wasn't in the repo and was stale | `wilo/coach.md` + `coaching_method` tool + per-user profile | #48 |
| Legacy top-level collections were world-readable and writable | Tracker per-user only; rules lock everything outside `users/{uid}` (2026-10-12) | #15, #69 |
| The tracker saved silently ("Downloaded" even when Firestore failed) | "Saved ✓" only after Firestore confirms, else "Save failed — retry" | #29 |
| Public repo with personal data | Decided: the repo stays public; Thom is fine with his own data in it. Other users' data needs their OK | #52 |

---

## 8. If we built it again

**Keep (these were right):**
- **One engine, thin adapters.** `wilo/data.py` holds all the logic, and the CLI and the MCP server are thin wrappers. It's also the seam for a future database switch.
- **The uid never comes from the AI.** It comes from the token or the config. Plus **dry-run writes** with explicit approval.
- **Free-text exercise names + a loose schema**, formalized only where real data needed it.
- **A plain HTML tracker** with no build step.
- **Session notes and docs in the repo**, so cloud and local sessions share one memory.

**Change:**
1. **Per-user paths and required sign-in from day one.** The top-level collections caused the migration (#27), the open rules (#15), the dual writes in the tracker, and the "new user sees Thom's workout" bug.
2. **Choose hosting with billing sorted up front.** We designed for Cloud Run (no keys, ~$0) and then hit the card problem at deploy time. Now the database is on Google and the server on Render, with a key file bridging them. One platform, or knowing the payment constraint early, would have been simpler.
3. **Put the coach in the repo from the start.** Instructions are code (`principles.md` says so). The skill living only on claude.ai is why it went stale unnoticed.
4. **Infrastructure as code from the first deploy:** `render.yaml`, pinned dependencies, rules deployed by CI, tests in CI. All cheap on day one and annoying to retrofit.
5. **Backups before real data:** delete protection plus a scheduled export on day one.
6. **A private repo (or a separate private notes repo)** for anything personal: health notes, training conversations.
7. **Design the data shape (#19) before building the tracker.** The tracker's internal shape leaked into the data (`instanceId`, `exId`, `swapped`), and the old coach skill still encodes an even older one.
8. **Fewer moving parts at the start:** we built the program builder, the swap feature and the legacy `sessions`/`programs` shape before the loop was proven. Most of that is now cleanup (#30).
