# 2026-10-05 (Mon, afternoon): data cleanup, MVP changed to the coaching loop

Follows `2026-10-05-cleanup.md` (morning: branches, stray files, #22–#24).

## Big decision: MVP question changed
- **Old:** does an AI-generated workout make the workout better?
- **New:** does an AI *plan*, delivered to Thom's phone day by day, make his training better?
- **Why (Thom):** WILO hands out workouts like a Pez dispenser. There are no days of the week and no plan, so it's easy to change things on a whim and hard to stay motivated. What matters is talking about what to work on and having WILO lay out a plan that does it. The coaching itself lives in one Claude chat and is lost when it ends.
- **The loop:** conversation → plan → calendar → workout → review → adjust. Written up in **#25**.
- `.claude/instructions.md` and `memory.md` updated in **PR #26** (open).

## Issues updated
- **#25 (new):** coaching loop. Data: profile, plan, assigned + `scheduledFor`, completed, review, all under `users/{uid}`. Smallest-version checklist. Prior art: `dev` commits `2c2ff5d` (auto-load today from microcycle) and `ad4109d` (week view).
- **#19:** depends on #25 (schema needs `plan`, `review`, `scheduledFor`) and on #15 step 2. Targets `users/{uid}/...` only. Keep the service-account key for v1.
- **#15:** new sub-item under step 3: make sign-in required in the tracker before step 4 locks the rules. A signed-out Finish would be denied.

## Firestore data cleanup (done)
- **Backup first:** `data/backup-2026-10-05/` (gitignored, **local machine only**). All top-level collections plus `users/{uid}/...`.
- **Deleted 9 duplicate or empty docs from `completed`:** `27-sep-15:24-legs-`, `prog_1790535871431-1790786264482`, `01-oct-07:42-push-`, `01-oct-07:42-push--8isj`, `03-oct-15:25-shoul-rwec`, `05-oct-14:25-pull--pab9`, `05-oct-14:31-pull--lwk2`, `05-oct-14:32-pull--5v61`, `24-sep-20:47-shoul` (kept `21:17`). Also deleted the `rwec` and `pab9` copies under `users/{uid}/completed`.
- **`completed` now has 8 workouts on 6 days** (Sep 24 – Oct 5). The last three logged 83–100% of their sets.
- **Likely cause of the duplicates:** Finish shows no "saved" confirmation, so Thom tapped it again. A cheap fix is worth doing.
- **Key:** service account at `~/wilo-claude/service-account.json` (project `wilo2-1ee44`). uid `iHi6rRlVU3XpYN1KHO0nwbKuZiE3` confirmed (the only `users` doc).

## Where it stopped
- **`scripts/copy_to_user.py`** is on branch `feat/copy-to-user` (pushed, no PR). It copies top-level `assigned` + `completed` into `users/{uid}`. Dry run by default, never overwrites or deletes. **Not run with `--write` yet.**
  - Waiting on: Thom's call on the 09-24 `assigned` docs. `19:32` looks like a draft replaced by `20:44`. `18:08` was the legs version.
  - `programs` is left out on purpose ("what assigned used to be", old shape). Don't touch it yet.
- `assignedFor` is when the coach posted a workout, not the day it's for. That's why #25 adds `scheduledFor`.
- `users/{uid}/test/ping` is left over from the deleted auth test page and can be deleted.
- Deploy is still pending, to take the stray `fe/` files off the live site. Then check that `/PR_REVIEW.md` returns 404.

## Next
1. Merge #26.
2. Answer #25's open questions: does a block cover 1 week or 4, what happens to a missed day, and is the profile its own doc? They decide the plan schema.
3. Decide on 09-24 `assigned`, then run `copy_to_user.py --write` and open a PR.
4. Finish shows "Saved ✓" and disables the button (stops duplicates).
5. #19 against the #25 schema. Still needs `wilo_fs.py` from the claude.ai skill (only `SKILL.md` synced locally).
6. Triage stale issues: #1, #2, #5, #7, #8, #11.

## Open
- PRs: #26. Branch `feat/copy-to-user` (no PR yet).
- Issues: #25, #19, #15, #14 (parked), plus the stale ones above.
