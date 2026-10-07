# 2026-10-07 (Wed): wilo_data.py proven with Claude, history cleaned, history/names/update

**Restart note.** If a session restarts (or picks up via `/rc` on the phone), start here. Yesterday's context: `2026-10-06-workout-schema-and-script.md`.

## Where it stopped
- **PR #34 is open:** `history`, `names` and `update` added to `scripts/wilo_data.py`, with 16 tests. Tried on the real database (history queries, update dry runs). **Merging it closes #19.**
- **Thom was trying `update` himself:** `get` → edit `data/oct5.json` (rename `"Calf raise. "` → `"Seated calf raise"` in `05-oct-09:22-shoul-75m0`) → dry run. Whether to `--write` it is his call. It would be the first real clean-up edit.
- **Tomorrow (Thu Oct 8, lunch):** `chest-biceps-oct-8` is posted and Load shows it. After he trains: review it together, then plan the next one.

## Done today
- **#19 end-to-end test passed.** Claude read history with the script, planned with Thom, posted with `assign --write`, and **Load in the app showed it.**
- **History cleaned (one-off, done directly, no repo script).** Thom's calls: delete exact duplicate `qq43` (Oct 6), delete `oct1-delts` 08:12 (Thu was the 18:36 session), delete `pull-press` 14:28 (Mon was the 09:22 shoulders), delete Sep 30 12:48 (UI test), move `legs-sept-23` to **Sep 23 7:00 pm**. Backup before: `data/backup-2026-10-07/` (local only).
- **History copied into `users/{uid}`** (#27 closed): 8 assigned and 4 completed, plus Sep 30 legs converted from old `sessions`. **The script now sees all history: one completed workout per training day,** Sep 23, 24, 27, 30, Oct 1, 5, 6.

## Decisions and why
- **One-off data chores aren't tracked in git:** just do them (backup, dry run, run), without a branch, PR or repo script.
- **Exercise names stay free text** (no catalog or IDs). `history` matches only cosmetic differences: case, spacing, punctuation, plurals, word order. **Synonyms** (`crane-plane` vs `Basic cranes`) are judged by Claude using `names`, in conversation.
- **Data clean-up happens during planning conversations:** Wilo reviews the data, and it's either updated (`update`) or left alone.
- **`update` added now** because it's cheap and that flow needs it. It replaces the whole doc, the dry run shows a field diff, and it refuses missing docs and `id` changes.
- **#29 skipped for now:** timed exercises show "reps", not "secs".
- **Product idea (parked):** semantic search over exercise names, e.g. "find what this tracker calls squats". It solves a common tracking pain. v0 = the LLM reads `names` (works today); later, embeddings, or a few hand-picked dimensions (movement pattern, equipment, one side or both), which could also suggest swaps.
- **Product idea (parked):** a progress doc for each user. First entry: **Mon Oct 5, shoulder press machine at full range of motion with both shoulders, pain-free.** Still weak, clearly improving.

## How to run things
From the repo root, on `main` once #34 is merged:
```bash
.venv/bin/python scripts/wilo_data.py completed --limit 4
.venv/bin/python scripts/wilo_data.py assigned --limit 2
.venv/bin/python scripts/wilo_data.py get completed <docId>
.venv/bin/python scripts/wilo_data.py history "bench" [--limit N]
.venv/bin/python scripts/wilo_data.py names
.venv/bin/python scripts/wilo_data.py assign workout.json [--write]
.venv/bin/python scripts/wilo_data.py update completed <docId> edited.json [--write]
.venv/bin/python -m unittest discover tests -v
```
- `config/wilo.json` points to the key at `~/wilo-claude/service-account.json` (laptop only).
- **Post one workout at a time:** Load opens the newest `assignedFor`. `assignedFor` = the date the workout is for (e.g. `"2026-10-08"`).
- **Phone access today:** run `/rc` (Remote Control) in a local session. Claude keeps running on the laptop, so the script and key work. #31 is the proper connector.

## Thom's coaching preferences
- **No cues.** Warm-up first, then **stretches right after**. The lunge stretch was skipped Sep 24, 27 and 30, and done 4/4 once moved to #2 on Oct 6.
- **Right leg is the weak side.** Rule: *if the right crane fails, regress to basic cranes and skip step-ups.* Track cranes with `custom_name: "Side"` (R/L), right first.
- **Cranes at the very start** ("otherwise I'll wimp out").
- **Decline curl (flossing)** before bench. Part stretch; track weight and reps (15 lbs for now).
- **Wants a good arm day:** biceps focus (no triceps in `chest-biceps-oct-8`).
- Progress only what was fully done; repeat what wasn't. Custom columns: `Risers`, `Side`, `Direction`, `Assistance`.

## This week so far
Mon Oct 5 shoulders (14/16), Tue Oct 6 legs (34/42), Thu Oct 8 chest + biceps (planned). **Pull hasn't been done this week.**

## Open PRs and issues
- PR #34: history/names/update. Closes #19.
- PR #33: harness updates + Oct 6 session note.
- #29: tracker changes (Saved ✓, read `timed`, Load by `assignedFor` date). Saved ✓ is the real fix for duplicates.
- #31: use the script from Claude anywhere (connector). #30: remove the unused swap feature.
- Parked: #25 coaching loop, #28 full schema. Later: #14, #15.
