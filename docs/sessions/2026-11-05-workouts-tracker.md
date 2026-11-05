# 2026-11-05: #126 tracker rebuilt and shipped (PR #146)

Continues `2026-11-05-token-cost-and-workouts.md`. #126 is **live**: #146 merged as `7fdf049`, rules deployed,
all 4 users migrated, Hosting and Render on the new code. Thom confirmed on his phone that a coach change to
today's cardio ("50 minutes") reached the tracker live. #126 and #145 are closed; #129 closed as superseded.

## Done

Tracker, one commit per step, each unit-tested (`tests/fe/*.mjs`, run with `node`):
1. Reads `users/{uid}/workouts`; one doc = one timeline stop (`done` if `status` is done, else planned).
2. `saveWorkout` writes only `log`, `logBase`, `status`, `updatedAt`, `finishedAt`; creates a plan-less workout on
   its first save; `finishedAt` is kept once set.
3. Live `onSnapshot` listener; a coach change to the open workout merges in by `exId` (logged sets, renames,
   deletions as `removed`, own `u-` exercises survive). A rename no longer changes the `exId` (#145's root
   cause). Opening a workout whose log is behind the plan (`logBase` < `diffs.length`) merges on load.
   Pre-#126 drafts are remapped by name to the plan's `x…` ids (every phone has a draft: `persist()` always saves).
4. Update bar removed.
5. `chat.js` (no refresh hook, no "tap Update" tip), `today.html` reads `workouts`, `admin-viewer` lists only
   `workouts` (otherwise it would show each workout up to three times after migrating).
Plus `migrate_to_workouts.py --user UID`, and the docs (connector guide, infrastructure, `.claude/*`, wilo-infra
skill; chat cache note fixed to 1 hour).

**Manual tests Thom ran on localhost:** read-only timeline (31 stops); autosave and Finish write the right fields;
a coach change (`change_workout`, made by Claude with Thom's OK) arrived live and kept a logged set and a rename.

## Decisions and why

- Step by step with a manual check for steps 2 and 3 (they change behavior); steps 4 and 5 were deletions and
  plumbing, so unit tests plus syntax checks only. Thom's call: test everything once the PR is up.
- Blueprint (#129's branch) was used for ideas, not applied as a diff: its doc diff would have deleted the
  "coach.md is the only place with coaching instructions" rule (it was cut from an older main).
- No emulator for the rules (Thom: it's awful). The rules get deployed at rollout; on dev they weren't enforced.
- **The dev link can't test the coach.** The dev/preview Hosting link talks to the Render connector, and Render
  deploys only from `main` (auto-deploy on every commit to it). Until the merge, Render ran main's old code
  (`update_workout` on `assigned`), so a coach change made from the dev link never reached `workouts`. Found when
  Thom's "cardio to 50 min" landed in `assigned` (3000 s) while `workouts` still had 1500. A separate Render
  service for a dev branch would fix that; not built (Thom: "we would need a dev branch for Render as well").
- Claude updated the tool references in `wilo/coach.md` (`recent_workouts`, `change_workout`, no Update step) at
  Thom's request; the coaching rules and wording are untouched. The test needle is now `'it shows up by itself'`.
- Standing OK from Thom: commit and push on a working branch without asking (saved in memory). PRs, deploys,
  Firestore writes and merges still need his OK.
- Local chat: `fe/chat.js` posts to `localhost:8000` when the page is on localhost, so run the connector on 8000
  (`WILO_CHAT_MODEL=claude-sonnet-5-5 .venv/bin/python -m wilo.mcp_server --http --port 8000`) and serve `fe/` on
  8001. Serving `fe/` on 8000 makes chat answer HTTP 501.

## Outside the repo: test data in Thom's account (uid `iHi6…E3`)

- **Migration done for all 4 users:** his 31 first (27 done, 4 planned), then the full `--write` added 28 more
  (24 + 3 + 1) and skipped his. `assigned` / `completed` are untouched everywhere and are now only the pre-#126
  backup (deleting them is #53, not urgent). The migration skips docs that already exist, so a change made on the
  old path after migrating is **not** picked up by a re-run.
- Backup: `data/backup-2026-11-05-pre-workouts/` (git-ignored, laptop only). The full run overwrote his uid's
  files from the earlier one-user run, so his pre-test copy is gone from that folder.
- **Drift never checked:** between the migration and the merge, changes on the old path (the live app and the old
  coach wrote `assigned` / `completed`) were not compared with `workouts`. Only today's cardio (3000 s in
  `assigned`, 1500 s in `workouts`) is known; Thom redid it through the coach after the merge.
- Test workouts Nov 6 (`02-nov-13:32-chest`) and Nov 7 (`02-nov-13:32-back-`) were used for the manual tests and
  then reset to `planned` (empty log, `logBase` 0, no diffs, no `finishedAt`/`updatedAt`); nothing is left over.
  Their pre-reset copies were only in the temporary session scratchpad.
- One stray `completed` doc (from a test tick on the old path) was deleted; a copy is in the session scratchpad
  (temporary). `04-nov-10:28-legs--ee7e` (a real in-progress copy) was left alone.

## Where it stops / next

The rollout is finished (order that worked: coach.md tool references, PR, migrate all, deploy rules, merge,
swipe the app away and reopen). Housekeeping done: #129 closed, `feat/126-workouts` deleted, #142's branch has
`main` merged in (conflict was only the version tag; merged rather than rebased to avoid a force-push on the PR).

**Still open:**
- **#142** (chat greeting): Thom reviews and merges; test the greeting on the new live-listener code first.
- **#143:** re-measure the coach chat cost around 2026-11-12 (new Console CSV + `scripts/token-cost/carried_load.py`).
- **#53:** deleting the old `assigned` / `completed` collections, whenever Thom decides.
- Not run in a browser by Claude: `chat.js`, `today.html` and the admin viewer after #126 (syntax-checked only).
- Finish stays tappable on a done workout (pre-existing, not part of #126).
- `coaching-evals/` and `ml/` labels still use the old tools (left alone on purpose).
