# 2026-10-29: #126 stays on Firestore

## What we talked about
Thom asked whether #126 (one `workouts` doc per workout: plan + coach diffs + log) should move to Postgres, since it needs a migration anyway.

## Decision: stay on Firestore (Thom agreed)
- The hard part of #126 is the design: the diff format, exercise ids, `apply(plan, diffs)`, and live tracker updates. That's the same on any database.
- Postgres would add an API server, live updates (SSE), server-side auth checks and DB hosting, which roughly doubles the issue.
- Keep `apply()` and the diff ops in plain Python with no Firestore imports, and keep the storage layer thin, so Postgres stays a cheap swap later.
- If we ever move, Supabase is the likely route (live updates, auth and a browser SDK, so the tracker talks to it directly). It gets its own issue, after #126 works.
- Recorded as a comment on #126.

## Next
- #126 "To decide": diff ops (add / remove / swap / move, field changes) and how exercise ids are made and kept stable.
- Or finish the `ml/` tool-call data on `exp/toolcall-data2` first. That work is still uncommitted (batch7/8, review_table, round2-review, score.py, train_synth.jsonl) and wasn't touched this session.
