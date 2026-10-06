# 2026-10-06 (Tue): first coached legs day, workout schema, wilo_data.py

## Decisions and why
- **Two agendas, A first.** A = WILO works for Thom. B = deliverable to others (#15, #14, #31). B only once A is proven.
- **MVP metric:** plan completion % (scheduled workouts done, sets logged ÷ planned). Engagement = after one plan, Thom builds another.
- **Coaching loop (#25) is parked.** We answered its questions (plans open-ended, posted a week at a time; fixed calendar; profile its own doc), then set it aside to get the read/write script working first.
- **Schema = semantic model, not a contract.** Thom: "You are trying to write a contract to not break current software and data. I am trying to extract what semantically a workout, exercise and set need to have for them to be useful information for a human."
  - No `exId`/`instanceId` linking. Exercise names are whatever Thom calls them, and an LLM can reorganise the data later if needed.
  - Order = array order (Firestore keeps it). There's no `order` field.
  - `assignedFor` = **the date the workout is for**, so the coach can lay out several days. The tracker still opens the *newest* one, so post one at a time until #29 is done.
  - `lbs`/`reps` can start blank `""`. Blank doesn't mean bodyweight.
  - `timed` is optional, defaulting to false. `cue` = coach advice, `note` = Thom's feedback. Both optional.
  - Swap/fallback has never been used, so it's dropped from the model (#30 removes the code).
- **YAGNI:** formalise only from real data. The full profile/plan/review schema (#28) was premature, so it's parked.
- **Per-side tracking uses the existing custom column** (`Side` = R/L). No schema change.
- **Postgres is on hold.** Build on Firestore.
- **Tests use `unittest`** (built in), not pytest. No new dependency.

## Context from the conversation
- **Legs workout (posted by the coach, done by Thom):** 34/42 sets. The lunge stretch, moved to #2, was done 4/4 after being skipped twice when it came last. **Right leg is the weak side** (no basic crane on the right; curls R 9,6 vs L 10,10). Thom's own rule: *if the right crane fails, regress to basic cranes and skip step-ups.* Recorded in #25.
- **How planning should feel** (#25 comment): start from history, edit by conversation, show the workout before posting, then review.
- **Sep 30 legs** was only in the old `sessions` collection, so the app never saw it (#27).
- **"Drag is the signal"** (`docs/drag_is_the_signal/`): models default to the common pattern, and repeated pushback marks where Thom's idea differs from it. The schema exchange is the first example.

## Where it stopped
- **PR #32** (`wilo_data.py` + schema + config + tests) is open. The read commands and dry runs were tried live. **A real `--write` waits for #29 "read `timed`"** (Thom chose to fix the tracker rather than work around it in the script).
- **The script only runs on the laptop.** Using it from Claude anywhere is #31 (connector, about 2–3 days). The interim option is a cloud session with the key as a secret.
- **Duplicate completed legs workout** `06-oct-09:20-legs--qq43` (exact copy of `09:16`, in both top-level and the user collection). Delete it? Not decided.
- **#27** still waits on the 24-sep assigned drafts decision.
- **Still pending:** deploy (stray `fe/` files are live), and deleting the merged `docs/mvp-coaching-loop` branch (needs `-D`).

## Outside the repo
- Backup: `data/backup-2026-10-05/` (this machine only).
- Key: `~/wilo-claude/service-account.json`. `config/wilo.json` points to it.

## Next
1. Merge #32.
2. #29: tracker reads `timed` directly. Then post the next real workout with `wilo_data.py assign --write` (#19 done).
3. #31 or the interim cloud session, to use the script from the phone.
4. #27 history migration.

## Issues and PRs
- #19: `wilo_data.py` read/write workouts. PR #32.
- #25: coaching loop (parked; decisions and the first review recorded).
- #27: migrate workout history into `users/{uid}`.
- #28: full data schema (PR, parked as WIP).
- #29: tracker changes (Saved ✓, read `timed`, lbs on timed, `note` vs `cue`, Load by `assignedFor` date).
- #30: remove the unused swap/fallback feature.
- #31: connector build plan (Claude anywhere).
- #14: connector design / multi-user. #15: per-user data + security.
- Closed as stale: #1, #2, #5, #7, #8, #11.
