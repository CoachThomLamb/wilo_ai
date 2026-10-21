# 2026-10-20 (late) to 10-21: new export merged, key scare, mid-workout change flow

Follows `2026-10-20-coaching-evals-and-paper.md`.

## Decisions and why
- **Mid-workout changes, for now without code (Thom's flow):** Finish → Claude reads the completed workout → writes a NEW assigned workout (`<id>-v2`, today) with the done sets already `done: true` plus the changed remainder, tagged `changedFrom` + `changeNote` → Load → Finish at the end. Works because the tracker keeps `done` on load (`makeExercise`), and a new id avoids #90 skipping the finished original.
  - The partial completed copy from the first Finish is **kept on purpose**: it records the change point (useful for evals). `changedFrom` lets history avoid double-counting.
  - Catch: Load picks the earliest unfinished plan, so an older unfinished plan would win.
  - The real fix stays #68: save as you go + merge on Load. ~30–45 min of code; phone testing needs a Firebase preview channel (a deploy, needs Thom's OK).
- **Where traces live going forward:** repo `coaching-evals/` is fine at n=1. Next step (not filed yet): the connector logs every tool call to Firestore `users/{uid}/tool_log` (time, tool, full args, dry run or write). That fixes the export's gaps (no times, summarized args) and covers Lijon automatically. Chat text stays a manual export. Lijon's chats don't go in the public repo without Lijon's OK.

## What happened
- **New claude.ai export merged** into `coaching-evals/traces.jsonl` (now 30 chats). 2 new: **Sep 9** (origin: generic plan caused anxiety; Hevy CSV of 2,267 sets as baseline; Thom's rule "rehab one end, play at the other") and **Sep 14** (pre-connector JSON → Drive → iPhone Files hand-off pain). 9 tool calls now carry full workouts. Existing records untouched, so notes keys stay valid.
- **Key scare:** a third-party app warned about a leaked key and offered to connect to GitHub (declined, correctly). Scan of PR #94 and #92 (files, full history, comments): **no service account key**. The flag was the public Firebase web API key (`AIza…`), in every front-end page since Sep 21. GitHub alert #1 resolved as won't-fix; restricting the key by referrer added to #51.

## Where it stopped
- Thom is trying the mid-workout flow at a new gym (paste-in instruction for the coach chat is in the conversation; it asks for dry run first, a `-v2` id, `changedFrom`, `changeNote`). After: check the two completed copies + the v2 assigned, then write the flow into #68.
- Still pending from 10-20: stray completed copies of `back-tri-pump-oct-10` (`fqox`, `au2t`, `ae49`) to delete, then re-pull `completed.json`.
- Open: where is the Hevy CSV (the pre-WILO baseline for the paper)? `~/wilo/wilo_workout_traces.jsonl` (the new export) sits untracked in the main checkout; its data is in PR #94.

## Next
- #68: build save-as-you-go + merge-on-Load; test on a preview channel.
- File the connector `tool_log` idea (Backlog unless Lijon needs it this week).
- Merge #92 and #94; commit `notes.json` again before merging #94.
- #51: restrict the Firebase browser key by referrer (Google Cloud console).

## PRs and issues
- #94: coaching evals (now also this note and the merged export).
- #51: comment added, restrict the Firebase web key.
- #68: mid-workout plan changes (flow above until it's built).
