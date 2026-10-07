# 2026-10-07 (Wed): wilo_data.py proven, history cleaned, MCP server, wilo package, connector sign-in

**Restart note.** If a session restarts (or picks up via `/rc` on the phone), start here. Yesterday's context: `2026-10-06-workout-schema-and-script.md`.

## Where it stopped (end of day)
- **Next: Thom reviews #36**, then #37, then #39. They're stacked. #35 is merged with a merge commit, so #36 needed no rebase and is retargeted to `main`. When one merges: retarget the next PR to `main` **before** deleting the merged branch, then delete it.
- **#38** (principles + sign-in design) is independent and open.
- **Repo is on `main`.** Claude Code's `wilo` MCP entry runs `python -m wilo.mcp_server` from the **editable install**, so it runs whatever is checked out. `main` has `wilo/`, so it works (✔ Connected).
- **Step C sign-in is built (#39), not tried for real.** The end-to-end test needs Thom at the laptop: `python -m wilo.mcp_server --http --auth`, then `claude mcp add --transport http wilo-auth http://localhost:8000/mcp`, a browser opens, Google sign-in, call a tool. This **writes the first real `oauth_*` docs to Firestore**, which needs Thom's OK first. Hosting needs Blaze (later).
- **Tomorrow (Thu Oct 8, lunch):** `chest-biceps-oct-8` is posted and Load shows it. After he trains: review it, then plan the next one.
- **Optional:** the `"Calf raise. "` → `"Seated calf raise"` rename in `05-oct-09:22-shoul-75m0` (dry run done).

## Done today (evening)
- **Thom's review of #35 led to two changes:**
  1. **"Instructions" is its own layer** (text written for the LLM: server `instructions=`, the tool docstrings, the coach skill). Added to `docs/principles.md` (#38), now **config / code / data / instructions / LLM**. Extraction tracked in **#40** (refinement, not urgent).
  2. **The path hacks were confusing**, so **WILO is now a Python package**: `wilo/data.py` (was `scripts/wilo_data.py`), `wilo/mcp_server.py` (was `mcp/server.py`), `wilo/auth.py`, `wilo/login.html`, plus `pyproject.toml` (`pip install -e .`), replacing `scripts/requirements.txt`. No `sys.path` anywhere, and no folder named `mcp` shadowing the SDK. CLI: `python -m wilo.data …`. #36, #37 and #39 were rebased onto it.
- **The rebase caught a real bug in #39:** with startup code inside `main()`, `AUTH` and `server` needed `global`, or sign-in mode would silently fall back to the config uid. Fixed, with a regression test (verified it fails without the fix).
- **#37:** 9 MCP tool tests, plus `--http` (Streamable HTTP, 127.0.0.1 only). Claude Code connected to it as a remote server.
- **#39 (step C):** OAuth provider (`wilo/auth.py`: hashed, expiring codes and tokens; rotating refresh tokens; only Claude and loopback redirects), Firebase login page, `--auth`. **54 tests** in total, including 11 in-process HTTP tests of the full flow. Live probe: `401` + discovery docs as Claude requires.
- **Docs (#38):** `docs/principles.md`; `docs/connector-sign-in.md`. The MCP SDK v2 provides the OAuth endpoints, and login reuses Firebase sign-in, so **no separate Google OAuth client** is needed.
- **Workflow rules from today:** we don't merge code that isn't right; fix it at the bottom of the stack and rebase up. Force-push rebased branches with `--force-with-lease`. Some git pushes from inside the session failed with GitHub 500s (after `/rc`); if that happens, commit and give Thom the push command.

## Done today (afternoon)
- **#19 closed** (#32 + #34 merged): `wilo_data.py` (now `wilo/data.py`) has `completed`, `assigned`, `get`, `assign`, `history`, `names` and `update`.
- **Local MCP server (PR #35):** `mcp/server.py` exposes the same functions as 8 tools (`workout_schema`, `recent_completed`, `recent_assigned`, `get_workout`, `exercise_history`, `exercise_names`, `assign_workout`, `update_workout`). Writes are dry runs unless `write=True`. Uses **MCP Python SDK v2** (`MCPServer`, not `fastmcp`). First real use: "what did I bench last time?" was answered through `exercise_history`.
- **The broken `wilo` MCP entry is fixed.** `~/.claude.json` pointed at the system `python3` and a non-existent `mcp/server.py`, so it failed every session. Re-registered with `claude mcp add wilo -s local -- /home/thom/wilo/.venv/bin/python /home/thom/wilo/mcp/server.py` → ✔ Connected. In a running session, use `/mcp` to reconnect after server changes.
- **Per-user (PR #36, #31 step B):** every `wilo_data` function takes `uid`, and only the CLI reads it from config. The MCP server uses one `current_uid()` (config locally, the signed-in user's token later). **The uid is never a tool argument.** 19 tests, including two-user isolation.
- **Remote Control (`/rc`) used from the phone.** It works: the same session runs on the laptop, so the tools and key work.

## Done today (morning)
- **#19 end-to-end test passed.** Claude read history with the script, planned with Thom, posted with `assign --write`, and **Load in the app showed it.**
- **History cleaned (one-off, done directly, no repo script).** Thom's calls: delete exact duplicate `qq43` (Oct 6), delete `oct1-delts` 08:12 (Thu was the 18:36 session), delete `pull-press` 14:28 (Mon was the 09:22 shoulders), delete Sep 30 12:48 (UI test), move `legs-sept-23` to **Sep 23 7:00 pm**. Backup before: `data/backup-2026-10-07/` (local only).
- **History copied into `users/{uid}`** (#27 closed): 8 assigned and 4 completed, plus Sep 30 legs converted from old `sessions`. **The script now sees all history: one completed workout per training day,** Sep 23, 24, 27, 30, Oct 1, 5, 6.

## Decisions and why
- **One-off data chores aren't tracked in git:** just do them (backup, dry run, run), without a branch, PR or repo script.
- **Exercise names stay free text** (no catalog or IDs). `history` matches only cosmetic differences: case, spacing, punctuation, plurals, word order. **Synonyms** (`crane-plane` vs `Basic cranes`) are judged by Claude using `names`, in conversation.
- **Data clean-up happens during planning conversations:** Wilo reviews the data, and it's either updated (`update`) or left alone.
- **`update` added now** because it's cheap and that flow needs it. It replaces the whole doc, the dry run shows a field diff, and it refuses missing docs and `id` changes.
- **#29 skipped for now:** timed exercises show "reps", not "secs".
- **Product idea (parked):** semantic search over exercise names, e.g. "find what this tracker calls squats". It solves a common tracking pain. v0 = the LLM reads `names` (works today); later, embeddings, or a few hand-picked dimensions (movement pattern, equipment, one side or both), which could also suggest swaps.
- **Connector sign-in (research, #31):** per-user access needs OAuth. "No sign-in" means anyone with the URL can use it, static headers are an org-only beta, and MCP tunnels are Enterprise-only. **Option A:** Google as the authorization server with our own OAuth client (~half a day, needs a spike). **Option B:** our own authorization server in the MCP server (~1–2 days). Host on Cloud Run with its own service account, so there's no key file on the server. Lock the Firestore rules (#15 step 4) before anyone else connects.
- **Product idea (parked):** a progress doc for each user. First entry: **Mon Oct 5, shoulder press machine at full range of motion with both shoulders, pain-free.** Still weak, clearly improving.

## How to run things
From the repo root, after `.venv/bin/pip install -e .` (once):
```bash
.venv/bin/python -m wilo.data completed --limit 4
.venv/bin/python -m wilo.data assigned --limit 2
.venv/bin/python -m wilo.data get completed <docId>
.venv/bin/python -m wilo.data history "bench" [--limit N]
.venv/bin/python -m wilo.data names
.venv/bin/python -m wilo.data assign workout.json [--write]
.venv/bin/python -m wilo.data update completed <docId> edited.json [--write]
.venv/bin/python -m unittest discover tests -v
```
- `config/wilo.json` points to the key at `~/wilo-claude/service-account.json` (laptop only).
- **Post one workout at a time:** Load opens the newest `assignedFor`. `assignedFor` = the date the workout is for (e.g. `"2026-10-08"`).
- **Phone access today:** run `/rc` (Remote Control) in a local session. Claude keeps running on the laptop, so the script and key work. #31 is the proper connector.
- **MCP tools:** in Claude Code (local), the `wilo` server exposes the same functions as tools (`mcp__wilo__*`). Prefer them over shell commands.
- **Git pushes from inside the session failed** after `/rc` (GitHub `500 Internal Server Error` five times; reads and `gh` worked). The same push from Thom's own terminal worked. If it happens again: commit locally and give Thom the push command to run in his terminal.
- **The key exists twice:** `~/wilo-claude/service-account.json` (used) and `~/.config/wilo/service-account.json` (same key, unused). Thom decides whether to delete the second.

## Thom's coaching preferences
- **No cues.** Warm-up first, then **stretches right after**. The lunge stretch was skipped Sep 24, 27 and 30, and done 4/4 once moved to #2 on Oct 6.
- **Right leg is the weak side.** Rule: *if the right crane fails, regress to basic cranes and skip step-ups.* Track cranes with `custom_name: "Side"` (R/L), right first.
- **Cranes at the very start** ("otherwise I'll wimp out").
- **Decline curl (flossing)** before bench. Part stretch; track weight and reps (15 lbs for now).
- **Wants a good arm day:** biceps focus (no triceps in `chest-biceps-oct-8`).
- Progress only what was fully done; repeat what wasn't. Custom columns: `Risers`, `Side`, `Direction`, `Assistance`.

## This week so far
Mon Oct 5 shoulders (14/16), Tue Oct 6 legs (34/42), Thu Oct 8 chest + biceps (planned). **Pull hasn't been done this week.**

## Open PRs and issues
- **Stack to review, in order:** #36 (tools act on a given uid) → #37 (MCP tool tests + HTTP) → #39 (connector sign-in). Merged today: #32, #33, #34, #35.
- #38: `docs/principles.md` + `docs/connector-sign-in.md` (independent).
- #40: move LLM-facing instructions out of code (refinement).
- #31: connector build plan (A, B and C built in the stack; hosting needs Blaze). #29: tracker changes (Saved ✓, read `timed`). #30: remove the swap feature.
- Parked: #25 coaching loop, #28 full schema. Later: #14, #15.
