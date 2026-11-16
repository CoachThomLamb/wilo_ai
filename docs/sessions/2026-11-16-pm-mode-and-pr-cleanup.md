# 2026-11-16: PM mode (#170) and the open-PR cleanup

Continues `2026-11-14-hiwilo-domain-postgres-pricing.md` (on `feat/landing-beats`) and the happy path
draft in PR #167.

## Why
Thom keeps losing threads between chats. He asked for "a persistent session that is the project manager
for Wilo", and then for a PM / CTO pass over the open PRs.

## Decisions

**The PM runner (#170):**
- Local, not cloud. A Python script on Thom's machine is the driver, started by a timer. Thom wants to read
  the code, and collecting facts doesn't need an AI: Python answers the facts, the AI only judges.
- Three syncs: 6:30 am, 3 pm, 8 pm (Toronto). He can ignore any of them.
- **3 pm is the end of Thom's day, not a check-in.** Agents can keep working after it. He hands work off at
  3 pm and sees the result at 8 pm.
- That replaced the earlier rule "nothing writes unattended". The limits now: only handed-off tasks, each
  with an issue; draft PRs only; no merge, deploy, Firestore write or `main`; a note per task.
- Claude's pushback, recorded in the issue: review is the slow step, not agent hours. Several PRs were
  already waiting on Thom. The hand-off is last in the build order and should start at one task a day.
- The PM keeps the record; Thom makes the decisions.

**The PR review.** Eight PRs were open; two were on the pipeline (landing page → talk to Wilo → track a
workout → pay).

| PR | Call | Status at time of writing |
|---|---|---|
| #161 landing beats | Claude said merge; **Thom: hold, it needs more design** | On hold |
| #167 happy path doc | Finish and merge | Thom is reading it. The interview findings are not in it yet |
| #158 coach.md day mode | Thom's to write | Waiting on Thom |
| #154 calendar experiment | Close | **Closed.** Branch `exp/calendar` kept, in case drag to move is wanted |
| #124 Wilo knows the workout on screen | Close (waiting on Thom's word) | Checked: its base (#123) was closed unmerged, it conflicts with `main`, and it reads workouts the pre-#126 way. The role prompt and the server ping reached `main`; the rest is in #171 |
| #118 Hevy import | Close, keep #111 | Not acted on. It writes to the pre-#126 layout, so it needs a rewrite, not a rebase. The landing page promises import and this is the only import code |
| #125, #130 `ml/` experiment | Ship without the real-chat data | Done, see below |

**`ml/` and data.** The two PRs touch no app code, but they held about 1.3 MB of Thom's own real chats
(95 messages with the replies around them), and the repo is public. Thom: take the data out, then ship.
- Removed from the PR: the eval set, the seeds, the test split and the per-item results. Kept: the
  synthetic training data and the code.
- Squash-merged so the files never enter `main`'s history.
- Done: #130 squash-merged, #125 closed as shipped inside it, checks and the deploy run on `main` passed,
  and the backup's checksums match. The two branches were kept, so the data is still public there and in
  GitHub's PR refs; removing those takes a request to GitHub support.
- Thom assumed the data is all in Firestore. Only about half is (the tracker chats). The rest came from
  claude.ai and Claude Code exports, so a copy was made outside the repo before removing anything.
- The branches are kept because the experiment write-up cites a commit on them, so the data is still
  readable there.

**Interview.** Thom interviewed one early user (the one who dictated workouts and then stopped). By pattern:
- Stopped because of travel, not because of the app.
- Liked most: talking in gym language and having it tracked with almost no corrections.
- Missed: looking back at earlier days (Review mode now covers it), "what did I do last time?", suggestions.
- Would let Wilo plan after four to six weeks of logging, and would log daily if told the payoff.
- So the gap is that Wilo never says what it can do next. The capability exists.

## Open decisions
- **`coaching-evals/traces.jsonl` is on `main` and holds real chats** (it is where half the eval data came
  from). Taking the data out of the `ml/` PRs did not make it private. Thom hasn't decided what to do.
- **#170:** how many hand-offs a day (Claude suggested one). Thom hasn't answered.
- **#161:** what the first button does while "Talk to Wilo" (#165) doesn't exist. Now behind the design work.
- **#166:** a 14-day trial ends before the four-to-six-week payoff the interview pointed at.

## Where it stopped
- `docs/pm-mode.md` (this PR) is a first draft of the PM instruction, for Thom to edit.
- Nothing of #170 is built. First piece is the current-state page; `.claude/instructions.md` is stale
  (early October) and should point to it.

## Next
1. Add the interview findings to #167 (no names), Thom reads, merge.
2. Close #124 (its missing pieces are in #171) and #118, if Thom agrees.
3. Thom: write #158; coach.md lines so Wilo says what it can do next; the follow-up to the interviewed user.
4. Decide `coaching-evals/traces.jsonl`.
