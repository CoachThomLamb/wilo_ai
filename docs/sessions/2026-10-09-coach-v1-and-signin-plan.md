# 2026-10-09 (Fri, late): Coach v1 and tracker sign-in planned, break until Sunday

Earlier today: `2026-10-09-connector-live-on-render.md` (connector live, infra review). Big picture: `docs/infrastructure-and-rebuild.md`.

## Where it stopped
- **Thom is taking a break until Sunday Oct 11.** No training today. `pull-triceps-oct-9` is still posted and still the newest, so Load shows it on Sunday. Ask how the right shoulder feels, then either use it or plan fresh. The date can be moved with `update_workout` (dry run first). He didn't decide.
- **Nothing in progress:** no open PRs, repo on `main`, clean.
- **Thom's to-dos:** delete the old `wilo-workout-coach` skill on claude.ai (it also syncs into Claude Code and describes collections and a script that no longer exist); post our findings on MCP python-sdk #3508 (draft in the earlier session; tracked in #55).

## Next, in order
1. **#15, tracker sign-in** (agreed):
   - Back up Firestore to `data/backup-2026-10-09/`.
   - Tracker PR: signed out shows only a sign-in button; Load reads only `users/{uid}/assigned`; Finish writes only `users/{uid}/completed` and shows **"Saved ✓"** or **"Save failed, retry"** (sign in again if the session expired; the draft is safe in localStorage). Test on the PR preview on the phone.
   - **After** the tracker is live: a rules PR removing the four `if true` blocks, deployed by hand (`firebase deploy --only firestore:rules`).
   - New-user test with a second Google account: the tracker shows nothing that isn't theirs; the connector plans into *their* tracker; Thom's view is unchanged.
2. **#56, remove the builder:** can go with or before the tracker PR.
3. **#48, Coach v1** (absorbs #40, now closed): spike what claude.ai's model sees from a connector → one coaching file in the repo → `users/{uid}/profile` + `get_profile` / `update_profile` → seed Thom's profile (dry run, approve) → tests and docs.
4. Separately: test the rebuild checklist in the infra doc. Decide #52 (public repo) before Thom's talk.

## Decisions and why
- **Coach = option C (#48).** The **method** (how to coach anyone) is instructions: one file in the repo, served by the connector to every user, no skill install. **Preferences** (injuries, likes, "no cues", right-leg rules) are **data** in a per-user profile. The coach is for any user, with a basic coaching method for everyone (Thom).
- **Instructions stay in the repo, not Firestore:** versioned and reviewed, deployed on merge. Thom floated a skill stored in Firebase; parked until non-developers need to edit it or we A/B test.
- **Plain sign-in, twice, once per device each** (claude.ai + tracker). The connector's token is held by Claude's servers, so it can't reach the browser.
  - Later: **same-domain login** (serve `/login` from `wilo2-1ee44.web.app`, so connecting Claude finds you already signed in).
  - **Magic link rejected for now:** it would need the connector key to mint sign-ins for any user, and the link acts as a password inside chat history. All for one tap.
- **The builder goes (#56):** Claude plans through the connector now, and the builder writes to the open `programs` collection.
- **Order: #15 before #48.** Without #15 a second user's tracker would load Thom's workouts.

## Open issues touched this session
- #48 Coach v1 (plan in its comments) · #40 closed into #48 · #15 sign-in decisions + later ideas · #56 remove builder (new) · #55 the SDK `/revoke` workaround.
