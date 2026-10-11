# 2026-10-10 (Sat): tracks A+B, e2e test plan, magic link, home screen

Previous: `2026-10-09-connector-live-on-render.md`. A parallel session is working on #15 (branch `feat/tracker-signin-required`).

## Where it stopped
- **PR #59** (this branch) waits for Thom's review: instructions now say tracks A and B run in parallel.
- Thom is watching whether the iPhone home-screen tracker **stays signed in** over the next days. If he's asked to sign in often, that's the friction to fix.

## Decisions and why
- **Tracks A and B in parallel (PR #59).** Thom: "we are doing two things at once... that's kinda startups." A (works for Thom) sets the pace; B (works for others) stays small, and a big B investment needs a real new user waiting on it.
- **Magic link re-assessed (#61).** Earlier rejected on security (comment on #15). Overstated: the connector key (`datastore.user`) can already read/write every user's data, so minting sign-ins adds little. Safe with single-use ~5 min codes tied to the OAuth session. Cost ~5–7 h. Parked until a new user needs it. Unverified: the connector's key file may already be able to sign custom tokens without extra roles (15 min check).
- **Home screen works today.** Thom added the tracker to his iPhone home screen and Google sign-in worked inside it. Claude had predicted it might break (popup in standalone mode, `authDomain` = `firebaseapp.com` vs app on `web.app`); it didn't. So:
  - The same-domain `authDomain` fix is optional hardening, only if sign-in breaks.
  - #61 loses its iPhone argument.
  - Left: icon + manifest + full-screen polish (~30 min, un-parks "PWA icons"; no service worker).
- **E2E connector test planned (#60).** Password-only test user with sign-ups disabled, real OAuth flow and MCP calls against Render, nightly + post-deploy. No admin key in GitHub. **Conflicts with the 2026-10-09 call** "a dummy user in prod is too risky, use the emulator." The difference: this user only acts through the connector's OAuth (reads + dry runs), never through the service account. Thom to confirm before building.

## Open PRs and issues
- #59: instructions, tracks A and B in parallel.
- #60: e2e test of the hosted connector. Do #46 (unit tests in CI) first.
- #61: magic link, one tap from Claude to a signed-in tracker. Parked.
