# Case study: why the coach chat was expensive

Tracking issue: #143. One-page version: `docs/case-study-coach-token-cost-summary.md`.

## The problem

- The in-app coach chat (tracker → `/chat` → Claude + WILO tools) cost more than it should.
- No complaints about speed. The issue was money.
- Question we asked: where do the tokens go, and are they helping the coach do its job?

## How the chat spends tokens

- The API has no memory: every call resends the coach method, tool definitions, start context and the **whole chat so far**.
- Prompt caching makes the repeat cheaper, not free: the first call writes the prefix at 1.25× (5 min) or 2× (1 hour) input price, later calls read it at 0.1×. The chat part's cache lasted 5 min (until #144), and rests between sets often run longer.
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
- Why it happened (Thom): the first tools were a rough first draft. We didn't know what we didn't know: they read a lot of
  extra data, and we didn't realize what that did to the context. Early on we also threw everything at the model on
  purpose, to steer its behavior with more context.
- Found by debugging: stepping through whole chats showed the tool calls, not the prompt, made the bloat. The fix was more
  Python: targeted tools, so the chat only gets the information it needs and nothing else.

## The fix

- **The real bill** (Anthropic Console CSV, Oct 24 – Nov 5): $9.83 total. The chat moved from Opus to Sonnet 5.5 on Oct 26; since then about $10/month for 4 users, ~$7–8 of it Thom. Target: $1–2 per person per month (to charge ~$10 and profit).
  - Since Oct 27: **5-minute cache writes 54%**, output 20%, 1-hour cache writes 17%, cache reads 9%.
  - So the biggest cost was rewriting the chat into the cache after more than 5 minutes between messages (rests between sets), not output.
- **Step 1, shipped in #144 (cheap, no quality risk):**
  - The chat's cache lasts 1 hour instead of 5 minutes.
  - `recent_completed` trimmed: no tracker bookkeeping or empty fields (~45% of the size on real data).
  - Both list tools capped at 7 (the coach had asked for up to 12).
  - `assign_workout` returns a summary, not the whole workout; `update_workout` lists at most 20 changes.
- **Found while fixing:** the coach writes the *whole workout* to change one thing. `update_workout` input averages 2.4k chars, 54% of the coach's visible output.
- **Step 2, shipped in #146 (#126, designed in #129):** one doc per workout; the coach sends small diffs (`change_workout`) instead of whole workouts. Also fixed #145 (a mid-workout change forked a copy and lost logged sets).
  - Input: no change. What the coach reads is a view, and the views were already trimmed in step 1. The storage change was a correctness fix, not a token fix.
  - Output: −11% (edits are small ops, not a rewritten workout). Output is the expensive kind (5× input).
  - Guardrail that mattered: had the tools sent the stored docs as #129 did, reads would have been 2.4–4× bigger (the doc holds the plan twice, the diffs and the log) and undone step 1.
- **The two problems, named:** the tools return more than the coach needs, and the coach calls them more than it needs to.
- **Step 3, shipped in #148:** two tools built on the new storage that answer in short text built by Python, not JSON:
  - `training_summary`: recent training, one line per workout (each done set as `reps@lbs`, notes, what wasn't done). 14 days = 4.1k chars on Thom's data; the old 7-workout read was 13.7k.
  - `current_workout`: the workout in progress or today's, one line per exercise with its `exId` (~100–400 chars).
  - Built from the real database, not the test fakes, which had hidden its shape: log order ≠ plan order (190 of 684 exercises were added by the user), the log's `timed` flag is wrong, weights change set to set, 812 of 2,215 sets have blank/0/missing weight.
- **Step 4, shipped in #149: we couldn't see the real numbers.** The API's token counts were only printed to the Render log, which we can't read and which isn't kept. Every request now saves them next to its chat, and `usage_report.py` turns them into dollars.
- **Step 5, PR #150 (found with step 4's log on day one):** the chat lasted all day, so after any gap of over an hour the expired cache rewrote the whole day's chat at 2×. The first evening message wrote 16.9k tokens: 9.1k fixed prefix (coach.md + profile + 16 tools; checked with the token counter and real calls) + 7.8k of the morning's chat. Fix: an idle hour starts a fresh chat (the coach still reads the data through the tools).
- Parked: embeddings (workout data is structured, so exact filters do the job; maybe later for free-text notes), model/effort changes (quality risk, needs evals).
- Why tools first, not a cheaper model: the waste was in the data, not the model. A smaller model risks coaching quality, and there were no evals yet to check it.

## Result

- **Modeled** (replay of the 33 stored chats, 182 user messages, same questions, today's data, `replay_tool_versions.py`; chars):

  | Tools | Input per message (with resends) | Median chat | Output, total |
  |---|---|---|---|
  | Original | 90k | 81k | 468k |
  | #144 | 57k | 57k | 468k |
  | #146 | 57k | 55k | 416k |
  | #148 | 47k | 24k | 415k |

  Input −48%, output −11%. With the 1-hour cache most resent input is a cheap read, so dollars fall less than volume.
- **Real, first logged chat (2026-11-05, 2 messages):** $0.096, $0.048 per message. Baseline: $9.83 for the 179 messages before the fixes ≈ $0.055 per message. 84% of the new chat's cost was cache writes (the all-day-chat rewrite, fixed in #150).
- **Re-measured 2026-11-18** (`usage_report.py`, Nov 5–17, 4 users, 102 messages): **$2.41 total, $0.024 per message**,
  down from $0.055 before the fixes (**−56%**). Where the dollars go now: cache writes 62%, cache reads 21%, output 17%.
  The heaviest user (Thom, 70 messages in 13 days) runs ~$4/month, so the $1–2 target holds for light users, not yet for
  daily ones. Next lever: cache writes. Not yet cross-checked against the Console CSV.

## Lessons

- Measure before optimizing. The obvious suspect (start context) was negligible.
- Look at *what the model is asking*, not only at what it costs.
- Log the real usage from day one. We modeled from characters for a week; one day of real counts found the biggest remaining cost (the all-day chat).
- A cache is an entry fee: it pays back with every read within the hour, and loses when one write is never read.
- Design reads from the real data, not the test fakes.
- Changing how data is stored doesn't change what the model reads; the tools decide that.
- Don't steer a model by stuffing its context. Give it only what the task needs; shape behavior with evals and, where
  it pays, fine-tuning (in progress: a smaller model trained on eval data, `ml/`).
- Let the model take a first pass before writing instructions. A long instruction doc written up front is its own
  bloat. Keep the instructions short, as guardrails that correct what you don't want, while fine-tuning (in
  progress) improves the model itself.

## How we measured

- Read-only scripts over `chat_threads/{id}/turns`: sum chars by block type and by tool, and the user message before each call.
- chars ÷ 4 ≈ tokens (rough). Real token counts were only in the Render logs (`chat: … in= read= write= out=`),
  which we can't read and which aren't kept. Since #143's usage logging, every request saves the API's counts
  next to its chat (`chat_threads/{id}/usage`); `scripts/token-cost/usage_report.py` turns them into $ per day,
  per message and per chat.
- Scripts: `scripts/token-cost/usage_report.py` (ongoing cost) and `replay_tool_versions.py` stay (run `PYTHONPATH=. .venv/bin/python scripts/token-cost/<script>.py`, read-only). The one-off analysis scripts behind this study were removed in #196; get them back with `git checkout c6bb0bb -- scripts/token-cost/`.
