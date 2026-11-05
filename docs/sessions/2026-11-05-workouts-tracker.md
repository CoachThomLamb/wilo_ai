# 2026-11-05: #126 tracker rebuilt on `feat/126-workouts`

Continues `2026-11-05-token-cost-and-workouts.md`. The whole of #126 is now on the branch (pushed up to the
handover note; the commits after it are local until Thom says push). No PR yet.

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
- Local chat: `fe/chat.js` posts to `localhost:8000` when the page is on localhost, so run the connector on 8000
  (`WILO_CHAT_MODEL=claude-sonnet-5-5 .venv/bin/python -m wilo.mcp_server --http --port 8000`) and serve `fe/` on
  8001. Serving `fe/` on 8000 makes chat answer HTTP 501.

## Outside the repo: test data in Thom's account (uid `iHi6…E3`)

- 31 workouts migrated into `workouts` for his uid only (27 done, 4 planned). `assigned` / `completed` untouched.
  The full `--write` skips docs that already exist, so these are not overwritten.
- Backup of that run: `data/backup-2026-11-05-pre-workouts/` (git-ignored, laptop only).
- Test leftovers in `workouts`: **Nov 7 (`02-nov-13:32-back-`)** finished as a test, one set logged;
  **Nov 6 (`02-nov-13:32-chest`)** in progress: one Dead hang set done, exercise renamed "Dead hangssss", and one
  coach diff (Serratus shrug 3 → 4 sets). Reset or delete them before relying on those days.
- One stray `completed` doc (from a test tick on the old path) was deleted; a copy is in the session scratchpad
  (temporary). `04-nov-10:28-legs--ee7e` (a real in-progress copy) was left alone.

## Where it stops / next

**Rollout, each step with Thom's OK:** 1. Thom rewrites `wilo/coach.md` for the new tools (it still names
`recent_completed`, `recent_assigned`, `update_workout`, "tap **Update**"); change the `'tap **Update**'` needle in
`tests/test_mcp_server.py` with it. 2. Push and open the PR (say in it: `coaching-evals/` and `ml/` labels use the
old tools, left alone). 3. `migrate_to_workouts.py --write` for everyone (backs up first). 4.
`firebase deploy --only firestore:rules`. 5. Merge (Hosting + Render). Then swipe the app away and reopen.

**Risks to check at rollout:**
- Thom's phone draft: it is remapped on first load, but finish or reset the in-progress workout first anyway.
- Not run in a browser: the final `chat.js`/`today.html`/admin viewer edits (syntax-checked only).
- The tracker's version tag (`v2026-11-05-workouts-s4`) is hand-set; bump it when merging.
- Finish stays tappable on a done workout (pre-existing, not in this PR).

## Open

- #142 (chat greeting): touches `fe/chat.js`, so rebase whichever merges second.
- #145: #126 fixes it; delete the empty `fix/145-update-forks-copy` branch.
- #129: close once the new PR is up, pointing to it.
- #143: re-measure ~2026-11-12.
