# Paper: coaching with an LLM (WILO, single-user study)

Outline in bullets. Thom writes the paper.

## Intro
- Goal: gym consistency (visits per week).
- Four levers:
  - Happy path: open the tracker, the right workout is ready, one-tap logging.
  - Flexibility: change the plan in a sentence, before or during the workout, without breaking the log.
  - Progressive, tailored training: built from your goals and injuries; you see yourself getting stronger.
  - Coach check-ins: a habit of reflecting on progress with a coach.
- Measure: gym visits per week (workouts logged).
- Open: the research question in one line.
- Open: why an LLM coach, not a fixed program or a human coach.

## System
- Tracker (`fe/index.html`): plain HTML on the phone; loads the next uncompleted workout (#90); one-tap logging.
- Coach: Claude in claude.ai, often by voice; reads history, plans and edits; follows `wilo/coach.md` + per-user profile.
- Connector (`wilo/mcp_server.py`): MCP tools on the user's own data, behind Google sign-in.
- Rule: code does the deterministic steps; the LLM only judges (`docs/principles.md`).

## Method
- n=1, the builder is the user, 2026-09-23 to 2026-10-18.
- 28 chat records: 16 claude.ai (exported) + 12 from local Claude Code sessions.
- Labeled by Claude: 16 coaching, 7 coaching + other, 3 dev, 2 product test. Thom to check.
- Data: `coaching-evals/traces.jsonl` (branch `coaching-evals`).
- Missing: baseline (how often Thom trained before WILO).
- Missing: is the export complete? Nothing between Sep 24 and Oct 9.

## Assessing the chats (methodology)
- Step 1, collect: claude.ai export + coaching from local Claude Code transcripts, one format (`traces.jsonl`: id, date, source, messages, tool calls).
- Step 2, first pass by Claude: read all 28, label each chat (coaching / coaching + other / dev / product test), tags, one-line note. Source of the 7 early findings.
- Step 3, human pass by Thom: per assistant reply, 👍/👎 + free-text note; one note per chat. Viewer: `coaching-evals/viewer.html` + `serve.py`; saved to `coaching-evals/notes.json`.
- No rubric yet, on purpose: open notes first so the criteria come from the data, not from a guess.
- Unit of judgment: one assistant reply, in the context of the chat so far.
- Joins: notes keyed by chat id + message index; `traces.jsonl` is append-only so the keys stay valid.
- Step 4, criteria: group Thom's notes into patterns, then a written rubric (e.g. brevity, held the line, used history).
- Step 5, LLM judge: grade replies against the rubric; check agreement with Thom's thumbs (target ~80%+).
- Step 6, use: rerun the judge when `coach.md` or the prompt changes; regressions show as numbers.
- Limits: one rater, who is also the user and the builder; ratings made weeks after the chats.

## Findings (early, n=1)
1. Used in the gym: 6 mid-workout edits (audibles, swaps, reorders).
2. Verbosity is the top friction, by voice (5 chats from Oct 13): "just ship it", "caveman mode", "don't read it back".
3. Wanting the workout drives doing it: Oct 9 "got bored and wanted a pump" (10/30 sets); Oct 10 "zero rehab".
4. Early access failures break the loop: 5 cases (no data access, failed save, read-only tools, "not connected", missing profile tool).
5. Method read, not always followed: `coaching_method` called in nearly every planning chat from Oct 13; once "follow the method" (#79).
6. Reflection is rare and user-led: 3 chats; the coach reviews only when asked.
7. Life context mixes in: calendar, todos or email in 4 coaching chats (#45).
- To pull: workouts per week over the 4 weeks.
- To pull: load trends (e.g. single-leg curl 40 to 55 lb, RDL 40 to 60 lb).

## The tension (hypothesis)
- Flexibility vs progression: the coach gives in to what the user wants today; the "good for you" plan loses.
- Giving in is often right: the user trained instead of skipping.
- Real question: when to hold the line, when to bend.
- Hint of negotiation: Oct 18 shoulder day "kept short, since it keeps getting skipped".
- Hypothesis: LLM coaches defer to the user in the moment (trained agreeableness), so written rules are easy to override.

## Limitations
- n=1, builder is the user (bias).
- 4 weeks.
- No baseline.
- The system changed during the study.

## Future work
- Write the policy down (rehab minimum: trade, don't drop).
- Evals: does the coach hold the policy under pushback?
- RL only if prompting fails; needs a reward (adherence + progression), sparse at n=1.
