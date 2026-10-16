# 2026-10-16: coach.md canary, board cleanup

Previous: `2026-10-12-coach-tool-todos-today-page.md`.

## Where it stopped
- **Canary rules are still live in `wilo/coach.md`:** "end every sentence with a smiley" (#80) and a dead hang rule (Thom's PR after that). Any coaching chat that authorizes the method follows them. They come out with #83.
- **Now:** #83 (clean up `coach.md` + the thin skill) and #84 (rewrite the MVP text). Thom writes both.
- Thom's profile is still empty: the test dry run in this session wasn't saved. He'll write it himself.

## Done
- #76 (coach profile) tested and merged: `get_profile` showed `exists: false`; the `update_profile` dry run returned a diff and saved nothing. 88 tests OK.
- #79: tested whether `coach.md` actually steers coaching (results below). Parked, findings in its comments.
- Board cleanup: every open issue has a status. Closed #25, #29 (plan support, parked), #48, #52. New: #81 (info page), #83, #84, #85 (small tracker fixes).
- Merged branches deleted, local and remote.

## Decisions and why
- **Focus is one workout at a time.** Thom parked everything about multi-day plans (load today's workout, `planId`/`assignedFor`, week strip, the plan loop). He closed #25 and #29 instead of keeping them: "keep things simple, we can rebuild it later". The MVP text in `instructions.md` still says "plan" until #84.
- **claude.ai treats `coach.md` as a possible prompt injection.** On the phone, `coaching_method` was called, but the smiley rule wasn't followed, and Claude's reasoning said "spotting unusual embedded instructions within tool output". With "Follow the method returned by the `coaching_method` tool" in Thom's own message, the smileys showed up. So the problem is the channel (a tool result), not the file's length or wording.
- **The fix is authorization from the user's side:** a thin skill ("when coaching with WILO, call `coaching_method` + `get_profile` and follow them"), replacing the stale `wilo-workout-coach` skill on claude.ai; shipped to others via #71. Dynamic content stays in the tools; the skill only gives authority. For #83: write `coach.md` as reference ("WILO's method: …"), not commands to the model.
- **Phone tests skip the local check.** Claude Code also gets the server `instructions`, which claude.ai drops, so a local pass says nothing about the phone.
- #81 (info page) is track B: build it only when a real new user is waiting.

## Lessons (working with Thom)
- Claude guessed a claude.ai menu path ("Settings → General → personal preferences") that doesn't exist. Say "not sure" and offer a test that needs no setting (here: authorize in the message itself).

## Outside the repo
- Worktree `.claude/worktrees/docs-agenda-language` (branch `docs/session-2026-10-12`, merged, clean) was left alone in case the other session uses it. `.claude/worktrees/feat-coach-profile` is locked.

## Open PRs and issues
- #83: clean up `coach.md` + thin skill (Now). #84: MVP text, one workout at a time (Now).
- #46: Python tests in CI (Next). #71: coach as a plugin (Next).
- #79: coach.md verification, parked with findings. #85: small tracker fixes. #81: info page.
