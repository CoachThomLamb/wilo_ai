# Voice spike, option 1: a live voice model inside the tracker (#78)

Tap the mic on the tracker and talk. Audio streams to OpenAI's Realtime model over WebRTC and its voice
plays back live, and you can interrupt it. It changes the workout on screen through tracker tools
(`update_set`, `add_exercise`, …); changed cards flash. Tap again to hang up.

## What it took
- `fe/voice.js` (about 100 lines): WebRTC, the data channel, and running tool calls in the tracker.
- `fe/index.html`: `window.wiloTracker` (`summary`, `apply`), the mic button, and the flash. Shared with option 2.
- `wilo/voice.py`: `/voice/call` swaps the browser's SDP offer for OpenAI's answer, using our key, with the
  coach prompt and tools. The browser never sees a key. Shared parts: tools, CORS, sign-in, allowlist.
- New dependency `openai`. Tests: `tests/test_voice.py`, plus a headless browser run against a fake peer.

## To try it on the phone
1. On Render: set `OPENAI_API_KEY` and `WILO_VOICE_UIDS` (your Firebase uid). `WILO_REALTIME_MODEL`
   optionally overrides the default, `gpt-realtime-mini`.
2. Deploy this branch to Render and the tracker to a Hosting preview.
3. Open the tracker from the home screen, tap the mic, say "drop bench to 175".

## Cost and limits
- Billed per minute of audio, roughly cents per minute (check OpenAI's pricing page). The coach isn't Claude.
- Changes are on screen only until Finish saves them, same as edits by hand. No dry run.
- It doesn't see your history yet (only the workout on screen). The connector's read tools could be added.
- The wake word ("Hey Wilo") isn't in. It would be the same work for all three options.
