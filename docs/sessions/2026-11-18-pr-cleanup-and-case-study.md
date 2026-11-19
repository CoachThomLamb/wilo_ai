# 2026-11-18: PR cleanup, case study, a new user's paper log

## What got done
- **Cleanup PRs merged** (all CI green, deployed): #205, #208, #207, #216, #214, #213, #209, #203, #215, then
  #212, #211, #202, #206, #201, #210. Tag `last-known-good` = c6bb0bb marks the state before any of it, for a rollback.
- **#206:** chat model default is now Sonnet 5.5. Checked first: Render's `WILO_CHAT_MODEL` = `claude-sonnet-5-5`.
- **#201 → #210 (sign-in):** #201 conflicted with #209 (it edited `today.html`, which #209 deleted); rebased, kept the
  delete. #210 was stacked on #201's old commit, so it was rebased with `--onto` to drop that commit. Thom tested
  sign-in on hiwilo.com after #201. **Not yet checked after #210:** tracker, Day and Week each load data.
- **Token-cost case study** finished and on main: `docs/case-study-coach-token-cost.md` + one-pager
  `docs/case-study-coach-token-cost-summary.md` (#217, DRAFT labels dropped in #219). Re-measured Nov 5–17:
  $0.024/msg vs $0.055 before (−56%).
- **Thom's stuck workouts cleaned** (5 deleted, 1 marked done); backup in `~/wilo-admin/data/`.
- **New user onboarded from a paper log:** 16 workouts transcribed from photos and imported with a new script,
  `~/wilo-admin/notebook_import.py` (same shape as the Hevy import: done workouts, no plan, sets in the log;
  duration + Garmin calories in the workout note). Their uid was added to `WILO_CHAT_UIDS` on Render.
- **Issue #218** opened from the data check: what counts as done (empty Finish), past planned workouts piling up,
  L/R logged as separate sets.

## Decisions and why
- Merge in small batches with a rollback tag, instead of one big merge: easy to see which PR broke what.
- Personal/life admin stays out of this repo entirely (it's public), session notes included.
- The paper-log importer lives in `wilo-admin` (private): it holds a user's real training data.

## Where it stopped / next
1. **Check after #210:** sign in on hiwilo.com, open tracker, Day, Week; each shows data. Broken → Revert #210.
2. **#179** (coach chat knows the workout on screen), then **#181** (top nav; needs a rebase onto main first).
3. **#204** (Reset on a done workout wiped its log): retargeted to main after its base (#202) merged. Hold: review
   it before merging.
4. **#158** (coach.md day mode): draft, Thom's to write. **#118** (old Hevy import PR): close; the import lives in
   `wilo-admin` now.
5. **Matt** to onboard: after he signs in, add his uid to `WILO_CHAT_UIDS`. **Sam** asked (by text) for a charts PR;
   if he says yes, open the "progress chart for a lift" issue.
6. Still open from before: remove `admin-viewer/` from main (moved to `wilo-admin`); delete old admin/Hevy branches.
7. Coach cut a user's volume without asking: a `coach.md` change for Thom.
