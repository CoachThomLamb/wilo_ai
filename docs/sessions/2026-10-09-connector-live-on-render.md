# 2026-10-09 (Fri): connector live on Render, pivot direction, pull day

Previous: `2026-10-08-connector-sign-in-verified-and-hosting.md`. Working guide: `docs/mcp-server-and-connector-guide.md`.

## Where it stopped
- **The connector is live and works from claude.ai on the web and the phone app:** `https://wilo-connector.onrender.com/mcp`. #31 is closed.
- **Today's workout `pull-triceps-oct-9` is posted.** After Thom finishes, check that it saved (`recent_completed`). The first Finish on Oct 8 silently didn't save.
- **Optional:** fix `finishedAt` on `09-oct-06:30-chest-7qmb` (it says Oct 9 06:30, the re-Finish time; the workout was Oct 8). Thom hasn't decided.

## Done today
- **Merged #44** (hostable: `--public-url`, `Dockerfile`). Thom ran the local Docker check himself and learned the OAuth discovery flow along the way.
- **Billing turned out to be off.** The project was linked to a credit-only billing account ("GDP Credit"), now closed, so `billingEnabled: false`. Google rejected Thom's prepaid card, and he has no credit card. So **no Cloud Run**.
- **Hosted on Render's free tier instead.** We compared Render, Koyeb (paid only now), Hugging Face Spaces (Docker needs paid), RunPod (credit burns hourly, unstable URL) and Supabase (TypeScript functions only, Postgres). Render needs no card and builds the `Dockerfile` from GitHub.
- **A dedicated service account `wilo-connector`** with only `roles/datastore.user`. Its key is the Render secret file. Thom first pasted the **firebase-adminsdk** key into the Render form, but replaced it before submitting, so it never reached Render. Key locally: `~/wilo-claude/wilo-connector-key.json`.
- **Firebase Auth authorized domain** added: `wilo-connector.onrender.com`.
- **Docs:** guide hosting section (Render, Cloud Run as the alternative), `instructions.md` Now/Next, `memory.md` status, Dockerfile comment.
- **Issues:** #45 (pivot, see below), #46 (CI for the Python tests; CI today only deploys Hosting previews).
- `gcloud` is installed (`google-cloud-cli-lite` via `omarchy pkg aur add`). It's on PATH only in new login shells (`/etc/profile.d/google-cloud-cli.sh`); otherwise use `/opt/google-cloud-cli/bin/gcloud`.

## Afternoon: infrastructure review (PR #54, stacked on #47)
- `docs/infrastructure-and-rebuild.md`: for Thom, the team, future LLM sessions, and **a talk Thom will give**. Starts with the one-minute version, then goes deep. Mermaid diagrams, a rebuild checklist (not tested yet; **testing it is the next separate task**), gaps, "if we built it again".
- Gaps filed: #48 coach skill (stale and outside the repo, the big one), #49 backups (none exist), #50 infra as code, #51 keys/access, #52 public repo vs. personal data (**decide before the talk**), #53 legacy cleanup.
- #55: our `/revoke` workaround for MCP python-sdk #3508. **Thom will post our findings upstream himself** (draft is in this session: 2.3.0 still affected, Claude Code repro, workaround, ask a maintainer to assign someone since fix PR #3512 was auto-closed).
- **Next new-user test** (Thom wants it before sharing): first fix the tracker (sign-in required, only `users/{uid}`, a clear saved/failed message), lock the rules (#15), then test with a second Google account. Read in the tracker code: today a new user would Load Thom's old top-level workout, and Finish writes to the open top-level `completed`.

## Decisions and why
- **Pivot direction (#45, Thom's call):** Wilo becomes **the one place for the day** (training + todos + events), with the coach on top. Claude argued for training-only plus connectors to Google Calendar. Thom rejected that: the problem is **his** context switching between apps, not the AI's access to the data. Order: connector first (done), then design the first new collection from real daily use. Rewrite "The MVP" in `instructions.md` when that work starts.
- **Coaching: plans were too rehab-heavy.** Oct 8 completion was 10/30. Thom: "I didn't want to do it, I got bored and wanted to just get a pump." New plan shape: **short rehab minimum (cranes + dead hang), then a pump block (machines, cables, higher reps)**, with extras optional. Don't plan the same muscle on back-to-back days (biceps Oct 8 → triceps Oct 9).
- **Right shoulder sore on bench Oct 8** ("gonna rest it"); a machine decline press at 180 × 15 was fine. No pressing in today's plan. **Ask how it is.**
- **Test database:** the Firestore emulator is the right option when the fakes stop being enough. A dummy user in prod is too risky (the service account bypasses the rules). Decide later.
- **Thom allowed Claude to comment on and edit GitHub issues without asking.** Merges, pushes, deploys and Firestore writes still need his OK.

## Outside the repo
- **Render:** service `wilo-connector`, free tier, auto-deploys every commit to `main`. It sleeps after 15 min idle (~1 min wake-up).
- **GCP:** service account `wilo-connector@wilo2-1ee44.iam.gserviceaccount.com` (key id `86f4606b…`). The old Firebase budget sits on the closed credit account and does nothing.
- **Keys on the laptop:** `~/wilo-claude/service-account.json` (admin, local use only), `~/wilo-claude/wilo-connector-key.json` (connector). There's still a duplicate admin key at `~/.config/wilo/service-account.json`, unused.

## Open PRs and issues
- PR (this branch): docs for the Render deploy.
- #45: pivot to the one place for the day. #46: CI for the Python tests. #31: connector build plan (hosting done; close after the phone test). #15: lock the Firestore rules before **anyone else** connects. #29: tracker `timed` + "Saved ✓". #40: instructions out of code. #30: remove swap.
