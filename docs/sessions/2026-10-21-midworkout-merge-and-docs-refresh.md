# 2026-10-21: mid-workout merge works, docs refreshed, Lijon gate

Follows `2026-10-21-export-merge-key-scare-midworkout-flow.md`.

## Decisions and why
- **Mission-critical before Lijon: only #77** (new-user test end to end: a new Google account can sign in, connect the coach, plan → log → Finish, and sees none of Thom's data). Everything else (de-"Thom" the tool descriptions, setup message, consent, backups) is nice to have. Precondition outside our code: Lijon's Claude plan must allow custom connectors.
- **After #77: mid-workout changes (#68).** Built as state-based merge, not event sourcing. A diff log (base + replayed diffs) was considered and parked: sync and conflict cost for the same gym experience. The research value (who changed what, when) goes to **#96** (connector change log) instead.

## What happened
- **#68 built, PR #95, tested on Thom's phone with a real workout (hamstring-legs-oct-20):** ticked sets save as you go (`inProgress: true`), the coach changed the plan (Dumbbell RDL → Back squat), Load merged (early Dragging sets kept, squat added), Finish → **one** completed doc `21-oct-10:06-hamst-0adq`, `inProgress: false`. Merge rule: logged sets kept as logged, unstarted sets from the new plan, started-but-dropped exercises keep their logged sets, plan's `done` flags ignored, same completed doc. Loading a different workout over logged sets now asks first.
- **Preview sign-in:** added `https://wilo2-1ee44--pr95-feat-midworkout-merg-juib2evp.web.app/__/auth/handler` (+ origin) to the OAuth web client in Google Cloud. Each new PR preview host needs this (infra doc §6).
- **Docs refresh, PR #97:** `infrastructure-and-rebuild.md`, `mcp-server-and-connector-guide.md`, `connector-sign-in.md` checked against `main` (15 tools, 88 tests, rules locked 10-12, coach in repo, one path #87, gaps open/closed). Live consoles not re-checked.
- **#96 filed** (Backlog): change log of every workout change.
- Board: #77 and #68 in Now (with #89, #93).

## Where it stopped
- **Merged 2026-10-21:** #95 (live tracker + new tool descriptions on Render), #94 (coaching evals), #97 (docs refresh). Still open: #88 (instructions).
- Docs don't yet describe `inProgress` / merge on Load (two lines in the connector guide and infra doc).
- Still pending: stray completed copies of `back-tri-pump-oct-10` (`fqox`, `au2t`, `ae49`) to delete, then re-pull `coaching-evals/completed.json`; Hevy CSV location (paper baseline).

## Next
1. Add the `inProgress` / merge-on-Load lines to the docs; decide on #88.
2. **#77 new-user test** with a second Google account. Then onboard Lijon.
3. Nice to have before Lijon: tool descriptions say "the user", not "Thom" (`wilo/mcp_server.py` INSTRUCTIONS and docstrings).

## PRs and issues
- #95: save as you go + merge mid-workout plan changes (closes #68), tested, merged.
- #97: docs refresh, merged. #94: coaching evals, merged. #96: change log (Backlog). #77: new-user test (Now).
