# 2026-10-07 (Wed): wilo_data.py proven, history cleaned, local MCP server, connector research

**Restart note.** If a session restarts (or picks up via `/rc` on the phone), start here. Yesterday's context: `2026-10-06-workout-schema-and-script.md`.

## Where it stopped
- **PRs to merge, in order:** **#35** (local WILO MCP server) → **#36** (tools act on a given uid) → **#37** (MCP tool tests + local HTTP transport). They're stacked, so each retargets to `main` when the one below merges. **#38** (principles doc + sign-in design) is independent.
- **Step C (remote connector) is designed, not built:** `docs/connector-sign-in.md` (#38). **Option B is the plan:** the MCP SDK v2 provides the OAuth endpoints, we write a provider, and the login step reuses the tracker's **Firebase Google sign-in** (same uid; probably **no separate Google OAuth client** needed). Next: build the provider and test locally with Claude Code over HTTP (no Blaze needed). Hosting needs Blaze, which Thom will set up later. Research is on #31.
- **Local HTTP works (#37):** `mcp/server.py --http` serves `http://127.0.0.1:8000/mcp` (localhost only on purpose, no sign-in yet). Claude Code connected to it as a remote server. Tests: 28, including 9 for the MCP tools.
- **Tomorrow (Thu Oct 8, lunch):** `chest-biceps-oct-8` is posted and Load shows it. After he trains: review it together, then plan the next one.
- **Optional:** the `"Calf raise. "` → `"Seated calf raise"` rename in `05-oct-09:22-shoul-75m0` (dry run done). `--write` is Thom's call.

## Done today (afternoon)
- **#19 closed** (#32 + #34 merged): `wilo_data.py` has `completed`, `assigned`, `get`, `assign`, `history`, `names` and `update`.
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
From the repo root, on `main` once #34 is merged:
```bash
.venv/bin/python scripts/wilo_data.py completed --limit 4
.venv/bin/python scripts/wilo_data.py assigned --limit 2
.venv/bin/python scripts/wilo_data.py get completed <docId>
.venv/bin/python scripts/wilo_data.py history "bench" [--limit N]
.venv/bin/python scripts/wilo_data.py names
.venv/bin/python scripts/wilo_data.py assign workout.json [--write]
.venv/bin/python scripts/wilo_data.py update completed <docId> edited.json [--write]
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
- PR #35: local WILO MCP server. PR #36: tools act on a given uid. PR #37: MCP tool tests + HTTP transport (stacked: #35 → #36 → #37).
- PR #38: `docs/principles.md` + `docs/connector-sign-in.md`.
- #31: connector build plan. Steps A and B are done (PRs above); step C research is recorded.
- Merged today: #32, #33, #34 (closed #19).
- #29: tracker changes (Saved ✓, read `timed`, Load by `assignedFor` date). Saved ✓ is the real fix for duplicates.
- #31: use the script from Claude anywhere (connector). #30: remove the unused swap feature.
- Parked: #25 coaching loop, #28 full schema. Later: #14, #15.
