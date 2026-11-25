# Case study: cutting an AI coach's cost per message by 56%

*Thom Lamb, WILO (hiwilo.com). Deep dive with all the numbers: `case-study-coach-token-cost.md`.*

## The problem

WILO's coach is a Claude agent inside a workout tracker. It reads and writes each user's training data through tools
(the same tools are served to the Claude app over an MCP connector). It worked, but it cost too much per message to
charge ~$10/month and make money. Target: $1–2 per user per month.

## What I found

- **Measured before optimizing.** Read-only scripts over every stored chat: where do the tokens go, and what was the
  coach trying to find out each time it called a tool?
- **Tool results were 55–70% of the chat history.** The user's own typing was under 2%. The prompt everyone suspects
  (start context) was negligible.
- **79% of one tool's output was bookkeeping** (IDs, null fields, flags). The training signal was 21%.
- **Every question the coach asked was a lookup or arithmetic** ("what's today's workout", "did I get stronger").
  We were paying an LLM to read raw JSON and do what a few lines of Python do exactly.
- **The biggest cost wasn't output, it was cache writes:** chats that outlived the 5-minute prompt cache (rests
  between sets) and all-day chats that rewrote the whole history after an idle hour.

Why it happened: the first tools were a rough first draft, and early on we gave the model everything on purpose, to
steer it with more context. We didn't know what that did to the bill until we stepped through real chats.

## What I did

1. **Trimmed and capped the tools**; 1-hour cache for the chat.
2. **Diffs, not rewrites:** the coach sends small changes instead of rewriting a whole workout (output −11%).
3. **Python answers the facts, the AI makes the judgment:** new tools return short text summaries built by Python
   (14 days of training: 4.1k chars instead of 13.7k).
4. **Logged the real token counts per request**, with a report in dollars per message, chat and user. One day of real
   data found the next fix.
5. **An idle hour starts a fresh chat**, so a stale cache never rewrites the whole day.

Kept the model (no switch to a cheaper one): the waste was in the data, not the model, and there were no evals yet to
prove a smaller model coaches as well.

## Result

- Modeled on all stored chats: **input per message −48%** (90k → 47k chars), median chat 81k → 24k.
- Real, Nov 5–24 (7 users, 183 messages): **$0.024 per message, down from $0.055 (−56%)**, and it held as usage
  nearly doubled. Light users are inside the $1–2/month target; a daily user is ~$4/month. Next lever: cache writes
  (60% of what's left).

## Next: the cache itself (modeled, not shipped)

Cache writes are now the biggest cost. Each coach call caches the new part of the chat for 1 hour, and a 1-hour write
costs 2× the input price (a 5-minute write 1.25×; a read 0.05×). Per message, with **P** = tokens already cached,
**N** = new tokens and **g** = minutes since the last message ($ per million tokens, Sonnet 5.5):

- 1-hour cache: `4·N + 0.10·P`
- 5-minute cache: `2.5·N + 0.10·P` if g ≤ 5, else `2.5·(P + N)` (the whole chat is written again)
- 5-minute cache + keep-alive: `2.5·N + 0.10·P + k·0.10·P`, with k ≈ g ÷ 4.5 pings while the user rests

Replayed on the real usage (42 chats, 183 messages): the median gap between messages is 42 seconds, but 25 of 141 gaps
are 5–60 minutes (rests, warm-ups). A 5-minute cache alone saves nothing: those rewrites eat the savings. A 5-minute
cache plus a keep-alive ping during rests: **$0.0211 → $0.0168 per message (−20%)**.

## Lessons

- Measure first, and look at *what the model is asking*, not only at what it costs.
- Log real usage from day one.
- A cache is an entry fee: it pays back on every read within its window and loses on a write nobody reads.
- Don't steer a model by stuffing its context. Give it only what the task needs; shape behavior with evals and,
  where it pays, fine-tuning (in progress: a smaller model trained on eval data).
- Let the model take a first pass before writing instructions. A long instruction doc written up front is its own
  bloat. Keep the instructions short, as guardrails that correct what you don't want, while fine-tuning (in
  progress) improves the model itself.

**Stack:** Python, Claude API (tool use, prompt caching), MCP, Firestore, Render, Firebase Hosting.
