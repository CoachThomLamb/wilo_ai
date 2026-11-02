# 2026-10-30: coach.md rewrite, coach.md as the only instructions, Kimi test chat

## What happened
- **coach.md rewritten with Thom, section by section** (PR #132, issue #131). Decisions and why:
  - **Three modes:** intra-workout, planning, listening. Thom rejected "check-in": it implies Wilo asks questions.
    Listening = listen, answer briefly, cut the noise.
  - **Quick one-line confirm before saves stays "for now".** Thom briefly wanted none (the coach just does it),
    then chose to keep it.
  - **Wilo may edit sets already logged.** Not supported yet: the tracker's Load merge keeps logged sets as
    logged, so this needs a write to the in-progress `completed` doc (see Next).
  - **No pain questions anywhere.** Injuries live in `limitations`; every flow that picks exercises skips anything
    that clashes with them. The "Always" section was deleted (Thom: "vague and messy", "a foot gun"); its useful
    rules moved into the flows.
  - **Planning flow rebuilt:** "a day or a week?", then new user → "regular split?" / "what do you want to focus
    on?"; with History → "want me to look at your recent workouts and guess your routine?", follow the pattern.
  - **Review:** praise only real standouts (else it's insincere), note in `notes` how the User reacts, read
    `notes` before praising next time.
  - **New User:** no interview. Explain Wilo in 2-3 sentences, offer home-screen setup, then plan.
  - **`fallback`:** a key in `preferences` (backticks = identifiers, stated in the doc). Thom's Profile now has
    ``- `fallback`: Crane-plane, 3x6 per side`` (written to Firestore with his OK).
  - **Flowcharts stay inside coach.md** until that gets painful (Thom's call); no skills split yet.
- **coach.md is the only source of coaching instructions** (PR #132): server instructions, tool descriptions and
  the tracker chat's ROLE now only say what tools do and point to coach.md. `write=False` stays the default.
  claude.ai ignores server instructions, so `coaching_method` + the `wilo-coach` skill remain the route there.
- **Kimi test chat** `ml/kimi_coach.py` (branch `exp/toolcall-data2`): Kimi K3.1 Pro on RunPod's public endpoint
  `moonshot-kimi` ($2/$10 per M tokens), coach.md as system prompt, real WILO tools, saves need `y`, prints tokens
  and cost per answer. One question with 2-3 tool calls ≈ 20-30k tokens in, a few cents.
- **ML direction changed:** Thom wants Qwen to *coach*, not only pick tools, and training targets to be what he
  would do, not what Claude did. Built `ml/review.py` (label viewer: Wilo vs base vs Kimi vs wilo-ft → labels).
  Recorded the v1 result: `ml/experiments/2026-10-29-wilo-ft-v1-beats-kimi.md` (43% vs Kimi 23%, reproducible).

## Things outside the repo
- RunPod key is in `~/wilo/ml/.env`. Thom's shell exports an old `RUNPOD_API_KEY` (401), so run the chat as
  `RUNPOD_API_KEY= ~/wilo/.venv/bin/python ml/kimi_coach.py`, or fix the export.
- `~/wilo/.claude/settings.local.json` now has `"worktree": {"bgIsolation": "none"}` so background sessions can
  edit the main checkout (Thom added it).
- RunPod: pod `zcnsapsjdjgyth` is gone; serverless endpoint `sm8revay9myk75` exists with 0 workers (bills nothing).
- The `wilo-coach` skill on claude.ai (not in this repo) still says "call `get_profile`"; update it after #132.

## Open PRs
- #132 (draft): coach.md rewrite + coach.md as the only instructions. Deploys with the connector.
- #133: CLAUDE.md points to GitHub's stacked PRs guide.
- #125: `exp/toolcall-eval`, the small-model experiment. `exp/toolcall-data2` (pushed, no PR) sits on top of it.

## Next
1. Thom reviews/merges #132; check the connector deploy. Then regenerate `ml/wilo_tools.json` (its descriptions
   are now stale) so the Kimi chat matches the server.
2. Test coach.md in the Kimi chat: off-topic mid-workout, logged-set edit, can't-do with nothing given, fallback,
   hamstring + RDL swap, review after a workout, "I hate lunges".
3. Parked, small (~50 lines): tracker subscribes to the assigned doc (`onSnapshot`) so Wilo's changes show without
   tapping Load. Logged-set edits need the `completed` doc path on top of that.
4. Thom wants a "what stands between us and a first real user" list, with Claude's opinions.
