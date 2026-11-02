# 2026-11-02: tracker timeline (‹ › instead of Load)

## What Thom asked for
Drop the Load button and be able to "move through the stack": step back in time to see what he did, forward to see what's planned.

## Decisions and why
- **‹ day › bar under the header.** One timeline by day: done workouts (`completed`, finished only) back in time, planned ones (`assigned` with no finished copy) ahead. A done workout sits on its plan's `assignedFor` day, not `finishedAt` (see the bug below), or on its finished day if the plan is gone. Skipped plans show in the past as "Planned · not done".
- **Only "Now" (the draft) is editable; other days are read-only.** That way, peeking at last week mid-workout can't touch logged sets. Editing past logs is parked; the coach can fix them with `update_workout`.
- **Load had two jobs, and both have new homes:**
  - A planned day has **Start** (with the same discard confirm, skipped when the draft is already finished).
  - The coach's mid-workout change (#68) shows as an **"Your coach changed this workout · Update"** bar. The tracker refetches when you come back to the app (`visibilitychange`) and when the in-app coach calls `assign_workout`/`update_workout` (`wilo-plan-saved` event from chat.js). Update is still a tap, not automatic, because an automatic merge would throw away edits to sets not ticked yet (#109/#120).
- **The draft now keeps its plan** (`plan` in localStorage), so the Update bar and Reset work after a reload. Drafts saved before this adopt the current plan on their first fetch.
- Boot behaviour is unchanged: with nothing in progress, it opens the earliest unfinished plan (#90).

## Where it stopped
- Code is written, `node tests/fe/timeline_test.mjs` and `cue_note_test.mjs` pass, and the script syntax-checks.
- **Not yet tried in a browser.** Next: a phone-size Playwright run with stubbed Firebase and auth.js (real-shaped data from `recent_assigned`/`recent_completed`), then on the phone via a PR preview (the `dev` channel). No PR has been opened; Thom hasn't asked for one yet.

## Found, not fixed
- `finishedAt` moves later every time the app opens with a finished draft: `draw()` → `sync()` → the quiet cloud save re-stamps it (Oct 31's workout reads Nov 1 18:42). That matters for anything that orders history by `finishedAt` (`recent_completed`, `exercise_history`). Fix: keep the first `finishedAt` once finished, or skip the quiet save when nothing changed.
