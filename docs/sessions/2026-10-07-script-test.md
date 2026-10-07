# 2026-10-07 (Wed): testing wilo_data.py with Claude, end to end

**Restart note.** If a session restarts, start here. Yesterday's context: `2026-10-06-workout-schema-and-script.md`.

## What we're doing right now
Testing #19's "done when": **Claude (local Claude Code) uses `scripts/wilo_data.py` to read Thom's history, plan the next workout with him, and post it, and Load in the app shows it.**

| Step | What | State |
|---|---|---|
| 1 | Read recent workouts: `wilo_data.py completed --limit 4` | ✅ Done. Script on `main` works and the tests pass |
| 2 | Plan today's workout with Thom (conversation) | **Next.** Ask what he wants to work on |
| 3 | Write the workout JSON, `assign` dry run, Thom checks, then `--write` | Pending |
| 4 | Thom opens the app, taps Load, and sees it | Pending. If it works, #19 is done |

Decided: **skip #29 for this test.** Timed exercises (dead hang, holds) will show "reps" instead of "secs" in the tracker. The numbers are right; only the label is wrong.

## How to run things
From the repo root on `main`:
```bash
.venv/bin/python scripts/wilo_data.py completed --limit 4
.venv/bin/python scripts/wilo_data.py assigned --limit 2
.venv/bin/python scripts/wilo_data.py get completed <docId>
.venv/bin/python scripts/wilo_data.py assign workout.json          # dry run: validates, shows path + doc
.venv/bin/python scripts/wilo_data.py assign workout.json --write  # posts to users/{uid}/assigned
.venv/bin/python -m unittest discover tests -v                     # 8 tests, fake db, no Firestore
```
- `config/wilo.json`: project `wilo2-1ee44`, database `wilo`, Thom's uid, and the key **path** `~/wilo-claude/service-account.json` (local machine only). `GOOGLE_APPLICATION_CREDENTIALS` overrides it.
- `assign` fills in `id` and `assignedFor` (now) if missing, validates against `schema/workout.schema.json`, and refuses to overwrite.
- **Post one workout at a time.** Load opens the *newest* `assignedFor`. The latest assigned today is `06-oct-07:11-legs-`.

## Workout JSON shape (minimal)
```json
{ "name": "pull-press-oct-7", "exercises": [
  { "name": "Dead hang", "timed": true, "sets": [ { "reps": 45, "done": false } ] },
  { "name": "Step up", "custom_name": "Risers", "sets": [ { "lbs": 30, "reps": 8, "done": false, "custom": "3" } ] } ] }
```
Exercise = `name`, `sets` (+ `timed`, `cue`, `note`, `custom_name`). Set = `reps`, `done` (+ `lbs`, `custom`). `lbs`/`reps` can be `""` (blank, fill in at the gym). Exercise order = array order.

## Thom's coaching preferences (for planning step 2)
- **No cues.**
- Warm-up first (dragging), **stretches right after**. They get skipped when they come last.
- **Right leg is the weak side.** Rule: *if the right crane fails, regress to basic cranes and skip step-ups.* Right side first on single-leg work.
- Progress only what was fully done; repeat what wasn't.
- Custom columns: `Risers` (step-up height), `Side` (R/L), `Direction` (Drag/Pull).
- Leg extension iso @ 115 faded to 30s, so the next target is 2 × 45s.

## Recent training (last 7 days)
Thu Oct 1 (shoulders), Mon Oct 5 (shoulders/pull-press: 88%, 100%), Tue Oct 6 (legs, 81%). Rest Fri–Sun. Completion is trending up. The next logical session is pull/press or shoulders.

## Data cleanup (low priority)
- **Exact duplicate:** `06-oct-09:20-legs--qq43` (copy of `09:16`, in top-level and user `completed`). Delete it? **Not decided.**
- **Same-day pairs:** Thom trained **once** on Thu Oct 1 and once on Mon Oct 5, but each day has two different completed workouts. Only Thom can say keep or merge. Belongs in #27.
- The real fix is prevention: Finish shows "Saved ✓" and works only once (#29).
- Oct 1 is only in the top-level `completed`, not the user collection (#27 not run), so the script doesn't see it.

## Open PRs and issues
- PR #33: harness updates + Oct 6 session note (open).
- #19: `wilo_data.py`. Merged in #32; this test closes it.
- #29: tracker changes (Saved ✓, read `timed`, Load by `assignedFor` date).
- #27: history migration (also the same-day dedupe).
- #31: use the script from Claude anywhere (connector build plan).
- Parked: #25 coaching loop, #28 full schema.
