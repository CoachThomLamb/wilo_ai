# 2026-10-10 (Sat): tracker sign-in live (#58), a pump day from Hevy

Previous: `2026-10-09-coach-v1-and-signin-plan.md`. A **parallel session** wrote `2026-10-10-tracks-e2e-magic-link-home-screen.md` (PR #59) on the same day, so read both.

## Where it stopped
- **#58 is merged and live** (`https://wilo2-1ee44.web.app`): sign-in required, Load/Finish only `users/{uid}`, "Saved ✓" only after Firestore confirms, a "Workout complete 💪 / I'm awesome" screen instead of the JSON download.
- **Thom is training now:** `back-tri-pump-oct-10` is posted. After his Finish, check it saved (`recent_completed`), then review it with him.
- **#15 is not done:** step 4 (lock the rules: remove the four `if true` blocks, deploy by hand) is next. Then the new-user test with a second Google account.
- **Open PRs:** #57 (yesterday's late note), #59 (the parallel session), and this note's PR.

## Done today
- **Backup** before changes: `data/backup-2026-10-10/` (local, gitignored). Nothing existed only in the top-level `assigned`/`completed`; all of it is already under `users/{uid}`.
- **#15 cleaned up:** steps 2 and 3 ticked (#27; `wilo/data.py` + the connector). The leftover tracker work became step "3b". Retitled "Per-user data: tracker sign-in required + lock the Firestore rules".
- **#58 tracker PR**, tested on Thom's phone:
  - The first test hit **"Unable to process request due to missing initial state"** in Safari's **in-app browser** (he opened the link from this session via `/rc` → Camera). The popup can't open there, the fallback redirect went through `firebaseapp.com`, and Safari's storage partitioning lost the state.
  - **Fix shipped:** `authDomain` = the page's own host on Firebase Hosting (it serves `/__/auth/handler` on every hosting domain). This needs `https://<host>/__/auth/handler` in the OAuth web client's **Authorized redirect URIs** (Google Cloud console, client `103580826325-rqlm28…`). Thom added `wilo2-1ee44.web.app` and the PR-58 preview. **The live one had a typo at first** → `redirect_uri_mismatch` after merge; fixed. Added to the infra doc's rebuild checklist.
  - Verified: sign-in (in-app browser), Load, Finish → "Saved ✓" → complete screen; a second Finish updated the same doc; nothing written top-level. Test entries deleted.
- **Kanban board:** GitHub Project "WILO" (`https://github.com/users/CoachThomLamb/projects/5`), with columns Backlog / Next / Now / Done, all issues + PRs #57/#58. **Thom still has to turn on** the Workflows "Item closed" / "Pull request merged" → Done and "Auto-add" (`is:issue,pr`). New issues #60/#61 (from the parallel session) aren't on the board yet.
- **#56** filed: remove the builder (`fe/builder.html`).
- **Workout:** Thom found `pull-triceps-oct-9` boring ("the workout sucks"). He wanted **zero rehab**, back + triceps pump. Built `back-tri-pump-oct-10` from his **Hevy export** and deleted the old one.

## Decisions and why
- **The same-domain `authDomain` fix shipped,** even though the parallel session found the iPhone home-screen app signs in fine without it. **Links opened from the Camera or the Claude app use an in-app browser**, and that path was broken. So it's a requirement, not optional hardening.
- **Magic link: two views on record.** The 2026-10-09 comment on #15 rejected it (the key would need to mint sign-ins for anyone). The parallel session's #61 argues the risk is smaller than stated (the connector key can already read/write all data). **Thom to decide**; parked either way.
- **Coaching:** today he wanted no rehab at all, just a pump. Preferences seen: Meadows rows, the Hammer machine pulldown over the cable pulldown, triceps pushdown → dip machine → skull-crusher push-ups as the finisher, no overhead triceps. All of this belongs in the profile (#48).
- **The JSON download is gone:** "Saved ✓" is trustworthy now, and the iOS download prompt was noise at the gym.

## Outside the repo
- **Hevy export:** `~/Downloads/workout_data.csv` (exported 2026-09-14; Sep 2024 → Sep 2026, ~2,260 sets, columns `exercise_title, start_time, set_type, weight_lbs, reps, …`). Laptop only. Useful history for planning; consider importing or summarizing it into the profile (#48).
- **Google Cloud OAuth client redirect URIs** now include `wilo2-1ee44.web.app` and the pr58 preview handler.
- `gh` now has the `project` scope.
- `.claude/worktrees/` (untracked) is from the parallel session's worktree.

## Open PRs and issues
- #57: session note 2026-10-09 (late). #59: instructions (tracks A+B) + the parallel session's note. This PR: this note + the redirect-URI rebuild step.
- #15: step 4 (lock rules) + the new-user test. #56: remove the builder. #48: Coach v1 (the profile should include today's preferences and the Hevy history). #60: e2e test of the connector. #61: magic link (parked).
