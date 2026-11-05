# 2026-11-03 to 11-05: PR cleanup, Train/Review, coach token cost, workouts rebuild (#126)

One long session (compacted once). It ends mid-#126: the engine, tools, migration and rules are done on
`feat/126-workouts`. The tracker is next and is handed to a fresh session.

## Done

- **PR cleanup:** #134 and #128 merged. #110 (fork PR) re-made as #137, failed on the phone, parked (#138).
  #117 dropped: dashboards get rebuilt on the fly when needed.
- **#138** (coach said "no workout today"): `recent_assigned` was newest first with limit 3, so today hid
  behind a week of plans. Fixed in #140 (`upcoming()`: earliest day first). Thom confirmed it works.
- **#136 Train/Review** (#141 merged): the tracker opens in Train (today's workout, no ‹ › bar, "No workout
  today" if none). A header link switches to Review. Thom chose the header link (A) over a tab bar (B).
  Tapping Review mid-workout shows "Whoa 🛑 Focus on your training — we'll review later. Go get those gains!"
- **#143 coach chat cost** (#144 merged, issue stays open for the after-measurement). See
  `docs/case-study-coach-token-cost.md` (draft, Thom fleshes it out) and `scripts/token-cost/`.

## Decisions and why

- **Cost target:** $1–2 per person per month, so Wilo can charge ~$10 and profit. The real bill (Console CSV,
  `~/Downloads/claude_api_cost_2026_10_07_to_2026_11_05.csv`): $9.83 since Oct 24, about $10/month on Sonnet.
  **5-minute cache writes were 54%** (every message after a rest rewrote the chat); output only 20%.
- **Python answers the facts, the AI judges; pull on demand, not just in case** (Thom). Embeddings parked:
  workout data is structured, exact filters do the job. Maybe later for free-text notes.
- **Model/effort:** not touched (quality risk, needs evals). Render runs `WILO_CHAT_MODEL` = Sonnet 5.5
  since Oct 26 (the code default is still Opus).
- **#142 chat:** an empty chat shows a canned "What do you need?" (never sent to the server); switching
  Train/Review starts a new chat (fresh context). Copy tip dropped.
- **#126 rebuilt fresh on main** from PR #129 as the blueprint (Thom: not a merge; #129 was 20 commits behind
  with 7 conflicts). Deviations from #129, all for cost:
  - list reads are a trimmed **view**: plan as it is now + log, no original plan, no diffs (`changes: N`),
    no empty fields, at most 7. "What did you change?" → `get_workout` (whole doc) or the chat's own history.
  - `assign`/`change` return an **outline** (exId, name, sets), not the whole plan.
  - `recent_workouts('planned')` is **earliest day first** (keeps #138). A skipped past plan comes first
    (same as main today); the coach has to notice the date.
  - migration: a **second copy** of a workout (#145's fork) becomes `done`, never a ghost "in progress".

## Where it stopped: `feat/126-workouts` (pushed, no PR yet)

Done and tested (110 unit tests): `wilo/data.py` (engine, views, CLI), `wilo/mcp_server.py` (tools
`recent_workouts`, `get_workout(doc_id)`, `assign_workout`, `change_workout`; `update_workout` gone),
`schema/workout.schema.json` (from #129), `migrate_to_workouts.py` (dry run: 4 users, 59 workouts,
0 invalid, 0 in progress), `firestore.rules` (from #129; main's rules unchanged since).

**Next: the tracker.** Blueprint: `git show origin/feat/workouts-one-doc:fe/index.html` (and its `fe/chat.js`,
`fe/auth.js`, `fe/today.html`, `tests/fe/timeline_test.mjs` changes). Rebuild on main's tracker, keeping
Train/Review, the Whoa modal and the timeline. The tracker:
- reads and listens to `users/{uid}/workouts` (live coach changes, no Load/Update bar: drop `changedPlan`,
  `updatePlan`, `mergePlan`'s plan-reload path) and writes only `log`, `logBase`, `status`, `updatedAt`,
  `finishedAt`; can create a plan-less workout; never deletes.
- merges a new plan into the log by `exId` (#129's merge: logged sets, renames, deletions and user-added
  exercises survive). #145's root cause was instanceIds regenerated on every plan load; `exId` replaces that.
- `fe/chat.js`: refresh on `assign_workout`/`change_workout` (was `update_workout`).

Then, still in this PR: `fe/today.html`, `admin-viewer/`, docs (`docs/mcp-server-and-connector-guide.md`,
`docs/infrastructure-and-rebuild.md`: line 176 still says "1.25× for the 5-minute chat", it's 1h now),
`.claude/instructions.md`, `.claude/memory.md`, `.claude/skills/wilo-infra/SKILL.md`.
`coaching-evals/` and `ml/` labels use the old tools: leave them, note it in the PR.

**Rollout (each step with Thom's OK):** 1. Thom rewrites `wilo/coach.md` for the new tools (it names
`recent_completed`, `recent_assigned`, `update_workout`, "tap **Update**"; `tests/test_mcp_server.py` pins
"tap **Update**", so change that needle with it). 2. `migrate_to_workouts.py --write` (backs up first).
3. `firebase deploy --only firestore:rules`. 4. Merge (Hosting + Render). Then swipe the app away and reopen.

## Open

- **#142** chat greeting + fresh chat per mode: open, Thom reviewing. Its branch `feat/136-chat-greeting`
  touches `fe/chat.js`, so rebase whichever merges second.
- **#145** (mid-workout change forks a copy, drops logged sets): #126 fixes it. Branch
  `fix/145-update-forks-copy` is empty; delete it. Clean up the orphan `completed` copy only if #126 stalls.
- **#143:** re-measure ~2026-11-12 (new Console CSV + `scripts/token-cost/carried_load.py`), fill the case
  study's Result. Next lever if still too high: a Python planning summary (~1.5k chars instead of raw history).
- #136 (keep open until #142), #139 (tests/CI review), #129 (close once the new PR is up, pointing to it).
- Visualization of the cost flow: https://claude.ai/artifact/DtPk3s9vJMA9ko2JN1c3m8 (private).
- Not verified: the Render deploy of #144 (no access from here). Next chat's `chat:` log lines should show
  `read=` where long rests used to show `write=`.
- Local clutter: worktrees under `/tmp/.../scratchpad/` (wt126, wt136b, wt145) and `.claude/worktrees/`.
