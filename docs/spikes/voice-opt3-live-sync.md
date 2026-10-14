# Voice spike, option 3: Claude app for voice, tracker updates live (#78)

You talk to the coach in the Claude app's voice mode. Claude edits the workout through the connector
(`update_workout`), and the tracker redraws as soon as Firestore has the change. Cards that changed flash.

## What it took
- `fe/index.html`: watch the loaded `assigned` doc (`onSnapshot`), merge the new plan into the workout in
  progress, and flash what changed. About 80 lines.
- `wilo/coach.md`: a "During a workout" section, so Claude edits the current doc and keeps the dry run short.
- No server changes, no new keys, no new cost.

## How the merge works
Exercises match by name. One the coach didn't touch stays exactly as you logged it. A changed one takes the
new plan but keeps sets you've checked off. One the coach drops survives only if it has logged sets.

## Testing on the phone
1. Open the tracker from the home screen and load the workout.
2. In the Claude app, start voice and say "drop my bench to 175". Approve the dry run.
3. The bench card should flash and update without a reload.

## Limits
- You're talking to the Claude app, not to Wilo. On iPhone, the tracker can be on screen only if Claude's
  voice keeps running in the background.
- It goes through the dry run, so each change takes two turns ("here's the change" → "yes").
