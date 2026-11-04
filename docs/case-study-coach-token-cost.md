# Case study: why the coach chat was expensive

DRAFT (bullets for Thom to flesh out). Tracking issue: #143.

## The problem

- The in-app coach chat (tracker → `/chat` → Claude + WILO tools) cost more than it should.
- No complaints about speed. The issue was money.
- Question we asked: where do the tokens go, and are they helping the coach do its job?

## How the chat spends tokens

- The API has no memory: every call resends the coach method, tool definitions, start context and the **whole chat so far**.
- Prompt caching makes the repeat cheaper, not free. The chat part's cache lasts 5 min, and rests between sets often run longer.
- So anything that lands in the history gets paid for again on every later turn.

## Evidence (2026-11-04, 28 chat threads)

- **Where the history goes:**
  - Tool results: ~55–70%.
  - Thinking: ~15–25%.
  - Coach text: ~15%.
  - The user's typing: under 2%.
  - Start context (date + profile): 200–1,800 chars. Negligible.
- **Which tools:** `recent_completed` (248k chars over 18 calls, max 51k) and `recent_assigned` (211k over 24 calls) were the bulk.
- **Why `recent_completed` was heavy:**
  - 10 workouts = 42k chars. The training signal (exercise, reps, lbs, done) = 9k chars. **21%.**
  - The other 79% is bookkeeping repeated on every exercise and set: IDs, null fields, flags, planned cue text.
  - The coach chose its own `limit` (up to 12), and nothing capped it.
- **What the coach was trying to find out** (from the message before each call):
  1. "What's my workout today?": a date lookup. It went wrong twice ("dude … the whole week is planned", #138).
  2. Mid-workout edits: the workout already on screen, plus logged sets. Usually two calls to find one workout.
  3. Planning the week: what was trained recently, body parts, last weights. Large full-doc dumps.
  4. Progress ("felt stronger"): did I improve, and on what.

## Insight

- All four are lookups or arithmetic. None needs judgment.
- We were paying an LLM to read raw JSON and do what a few lines of Python do exactly, for free.
- Principle: **Python answers the facts, the AI makes the judgment.** (Matches WILO's coach design: scripts do everything deterministic.)
- TODO Thom: your take. Why it happened (tools were built as thin DB reads early on?), and what it says about building with LLMs.

## The fix

- TODO: decided in #143.

## Result

- TODO: re-run the same measurements after the fix. Before/after table: chars per tool call, history per thread, cost per chat.

## Lessons

- Measure before optimizing. The obvious suspect (start context) was negligible.
- Look at *what the model is asking*, not only at what it costs.
- TODO Thom.

## How we measured

- Read-only scripts over `chat_threads/{id}/turns`: sum chars by block type and by tool, and the user message before each call.
- chars ÷ 4 ≈ tokens (rough). Real token counts are in the Render logs (`chat: … in= read= write= out=`).
- Scripts: `scripts/token-cost/` (run `PYTHONPATH=. .venv/bin/python scripts/token-cost/<script>.py`). Read-only.
