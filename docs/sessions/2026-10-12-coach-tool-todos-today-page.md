# 2026-10-11/12: rules locked, coach tool, todos, Today page

Previous: `2026-10-10-tracks-e2e-magic-link-home-screen.md`. Another session ran in parallel on low-level work and on how the Claude-side instructions get organized.

## Where it stopped
- **PR #74 (Today page, `fe/today.html`)** waits for Thom to test and merge. Preview: `https://wilo2-1ee44--pr74-feat-today-page-rz2pp8ay.web.app/today.html`. If Google sign-in fails on the preview host (not an authorized redirect URI), test locally: `git switch --detach origin/feat/today-page && firebase serve --only hosting` → `localhost:5000/today.html`.
- **#66 (life coach) is parked** until the other session settles how the Claude-side instructions are organized (method file, tool descriptions, `instructions.md`). Ready after that: a `today` tool, a day section in `wilo/coach.md`, and the MVP rewrite in Thom's words.
- The todo tools and `coaching_method` are live on Render; Thom checked from the phone and they work.

## Done
- **#15 finished:** open top-level rules removed (#69). Thom asked for the deploy; it was done by hand (`firebase deploy --only firestore:rules`), since CI only deploys Hosting (#50). Verified the `wilo` database's rules release updated.
- **#56:** the builder is removed (#70).
- **#48 PR 1:** `coaching_method` tool serving `wilo/coach.md` (#72).
- **#64:** todos (#73): `users/{uid}/todos` + `list_todos`, `add_todo`, `update_todo`, `delete_todo`. 13 tools in total.
- **Epic #63 (Today)** filed with #64–66; #65 is a separate page, not a shell refactor.
- Backlog review: #14 closed (built); #29, #30, #46, #50, #53 updated.
- Issues: #71 (coach as a plugin, later). Merged branches deleted.

## Decisions and why
- **Phone test: claude.ai passes only tool descriptions to the model, not the server's `instructions`.** Claude Code shows both, which is misleading. So the coaching method lives behind a tool.
- **Tool, not plugin (for now).** A plugin (skill + connector, installed from our repo via "Add marketplace", synced from GitHub) is what most people ship, but it adds install steps for a new user and is Claude-only. The tool needs nothing beyond the connector. Plugin parked in #71; it would reuse `wilo/coach.md`.
- **The method is generic; personal preferences are data.** Thom's rules (no cues, right side, …) go in the profile (#48 PR 2), not `coach.md`.
- **Todos skip the dry run** (workouts keep it). Taken as recommended; Thom didn't object. One line to change.
- **Separate `today.html`, not a shell + views refactor.** Thom chose the simpler step: the tracker he uses daily stays untouched. Revisit if a third page shows up.
- **Today page before the week strip** (#29 stays in the backlog).
- **Navigation:** Today → tracker via the workout card; tracker → Today via a small header link and "Back to Today" on the Workout complete screen.

## Lessons (working with Thom)
- **Don't probe live systems on the side.** While preparing the rules PR, Claude ran anonymous Firestore reads and chased an unexplained 403 through the rules and App Check APIs without saying so. Thom: "why are you querying firebase directly". Changes go branch → PR → merge; checks against prod get named and okayed first.
- **Do only what the issue says.** Adding "rules deploy in CI" to the rules PR was extra; Thom wanted just the PR.
- **Run the tests before every PR**, even docs-only ones.
- **Testing a PR's connector code:** Thom checks out the branch in `~/wilo` himself and reconnects the `wilo` server. Pointing a second server at Claude's worktree (`PYTHONPATH`) was too fragile. A branch can't be checked out in two worktrees at once, so Claude moves its worktree off the branch first.
- Claude force-pushed a rebased PR branch (#73); it should merge `main` into the branch instead.

## Open PRs and issues
- #74: Today page (`fe/today.html`).
- #66: life coach, parked. #48: coach v1, PR 2 (profile) left.
- #71: coach as a plugin, later. #60: e2e connector test (Thom to confirm the prod test user). #61: magic link, parked.
- #46: Python tests in CI, ready. #50: infra as code (rules deploy in CI).
