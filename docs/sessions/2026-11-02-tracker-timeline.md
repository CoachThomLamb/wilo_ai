# 2026-11-02: tracker timeline (‹ › instead of Load)

## What Thom asked for
Drop Load. Step back a day ("what was yesterday?") and forward to what's planned, in **the exact same view** as now.

## How this session went (read this, next session)
I built a first version before talking it through: read-only past days, a Start button, extra logic. Thom pushed back hard, and rightly so. The repo instructions say to workshop with him first, because he's the product guy. He also wants short replies, one question at a time, not big updates. He'd rather see a quick prototype on dev than talk at length, but agree on the shape before building.

## Decisions (Thom's)
- **Every day is the normal tracker, editable.** ‹ › opens that day's workout, and you log sets on whichever one is on screen. No Start button, and no rules about whether the one before is finished. If that leaves loose ends (unfinished workouts), the coach cleans them up later.
- **Finish and the "I'm awesome" screen stay as they are.**
- The Update bar for the coach's mid-workout changes (#68) stays for now, since Load was the only other way to get them. Thom hasn't really weighed in; see how it feels on dev.

## How it works
- The timeline has done workouts (`completed`, finished) and planned ones (`assigned` with no finished copy), sorted by the plan's `assignedFor` day.
- Opening a day: a done one opens its finished copy, and edits save back to it. A planned one opens its saved-as-you-go copy if there is one (so logged sets come back), else the plan.
- Leaving a day saves its logged sets first. If that fails, you stay on it.
- Browsing without edits writes nothing: a save is skipped when nothing has changed since the day was opened.
- `finishedAt` is kept once a workout is finished. Before this, every app open re-stamped it (Oct 31's workout read Nov 1), and editing an old day would have made it look like the latest workout to the coach.

## Checked
- `node tests/fe/timeline_test.mjs` and `cue_note_test.mjs` pass.
- A phone-size Playwright run with stubbed Firebase and auth.js covered: back to done days, forward to planned ones, logged sets surviving a round trip, no writes while browsing, the Update bar after a coach change, and editing an old day not moving its `finishedAt`. The script isn't in the repo.
- **Not tried on a real phone or real Firestore yet.** That's what the PR's dev preview is for.

## Next
- Thom tries it on dev and says what he wants changed.
