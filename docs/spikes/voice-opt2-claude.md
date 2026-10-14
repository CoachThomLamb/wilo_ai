# Voice spike, option 2: Claude inside the tracker, one turn at a time (#78)

Tap the mic once and talk. The phone's speech recognition turns each sentence into text. `/coach/turn`
sends it to Claude with the workout on screen and the recent conversation. The tracker runs Claude's tool
calls (changed cards flash), and the phone reads the reply aloud, then listens again. Tap to stop.

## What it took
- `fe/voice.js` (about 90 lines): the listen → send → apply → speak loop.
- `fe/index.html`: `window.wiloTracker` (`summary`, `apply`), the mic button, and the flash. Shared with option 1.
- `wilo/voice.py`: `/coach/turn` makes one Claude call per turn with the tracker tools, and returns
  `{say, ops}`. Tool calls aren't run on the server, so there's no loop. Shared parts: tools, CORS, sign-in, allowlist.
- New dependency `anthropic`. Tests: `tests/test_voice.py`, plus a headless browser run with fake speech.

## To try it on the phone
1. On Render: set `ANTHROPIC_API_KEY` and `WILO_VOICE_UIDS` (your Firebase uid). `WILO_COACH_MODEL`
   optionally overrides the default, `claude-opus-5-5` (effort low).
2. Deploy this branch to Render and the tracker to a Hosting preview.
3. Open the tracker, tap the mic, say "drop bench to 175".

## Cost and limits
- Billed per Claude call (cents per turn at most). Speech recognition and the voice are the phone's, so free.
- **Biggest risk:** iOS speech recognition may not work in the home-screen app, only in a Safari tab.
  Test this first. If it fails, the fix is a paid speech-to-text API, which is another vendor.
- Walkie-talkie feel: you wait for Claude after each sentence (a few seconds), and you can't interrupt it.
- The phone's built-in voice sounds robotic next to option 1.
- Requests use server-side refusal fallbacks (`fallbacks: "default"`).
