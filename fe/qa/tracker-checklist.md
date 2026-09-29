# WILO tracker — manual QA checklist

Manual test list for `fe/index.html`. Roughly in priority order for the MVP (Finish export → phone → gym).

## Boot & loading

- [ ] Fresh load on phone: seed program renders, all exercises visible, no console errors.
- [ ] After ~600ms, "Today's workout loaded" appears (if a microcycle exists for this week) — session name matches Firestore.
- [ ] No microcycle for the week: "No microcycle found for this week".
- [ ] Rest day (day not in `programs`): "Rest day — nothing scheduled today".
- [ ] Tap **Today** button manually — reloads today's program.
- [ ] Tap **Load** — pick a local JSON file, session name updates, exercises replace.

## Logging (core loop)

- [ ] Enter lbs and reps — stats bar volume updates live.
- [ ] Tap done ✓ — row turns green, set count increments, volume changes.
- [ ] Untap done — reverses cleanly.
- [ ] **Add Set** — copies previous set's lbs/reps.
- [ ] **Add Exercise** at bottom — inserts blank, cursor focuses the name field.
- [ ] Kill (×) an exercise — disappears, state updates.
- [ ] Timed exercise (Dead hang): no lbs column, only reps/secs — volume shouldn't include it.
- [ ] Custom field: type into "Custom field name" (e.g. "incline"), blur → table gets that column, values persist.
- [ ] **Swap** button on Smith OHP: swaps to fallback text/target; tap again → returns to original.

## Persistence

- [ ] Log a couple sets, refresh the page → draft restores, "Restored from …" shows.
- [ ] "Saved <time>" tick updates every ~400ms after edits.
- [ ] **Reset** with logged sets: confirmation dialog shows count; accepting clears back to program.
- [ ] Reset after a `Load` returns to the *loaded* program, not the seed.

## Finish (MVP-critical)

- [ ] Tap **Finish** — JSON file downloads to phone (iOS: Files app / share sheet).
- [ ] Filename format: `<prog-name>-HHMM-mmmDD.json`.
- [ ] Open the downloaded JSON — has `program`, `finishedAt`, `sessions[0].blocks[].exercises[].sets` with lbs/reps/done/custom.
- [ ] Firestore `sessions/{sessionId-timestamp}` doc appears with the same payload.
- [ ] If Firestore save fails, an inline "Firestore save failed: …" appears but the download still succeeds.

## Week view

- [ ] Tap **Week** — table shows Sun–Sat, today's row highlighted blue.
- [ ] Days with a scheduled session show plan name; other days show "Rest".
- [ ] Days with a finished session show session name + "N sets done".
- [ ] Tap **Today** (was Week button) — returns to logging view.

## Layout / mobile quirks

- [ ] Focus any input — page doesn't scroll away; keyboard shrinks list, not layout.
- [ ] Rotate portrait ↔ portrait after typing — no ghost scroll offset.
- [ ] Error path: throw a fake error or trigger a bad Load file — status line shows "Error: …" and holds ~8s, isn't wiped by autosave.

## Minimum smoke test

If short on time, run: 1–3, 7–9, 15, 16, 20–23. That's the MVP path.
