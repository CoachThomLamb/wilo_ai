# 2026-10-17 to 10-20: board for Lijon, tracker next-workout, coaching evals, paper outline

## Decisions and why
- **Week goal:** WILO ready for a second user (**Lijon**) + Thom documents his experience. Board realigned: Now = #77 new-user test, #79, #81 info page (first reader: Lijon), #83, #84, #88, #89 write-up, #93 demo video. #46 and #71 back to Backlog; #61, #49, #51 to Next.
- **Thesis (Thom writes it into #84):** goal = gym consistency (visits/week). Four levers: happy path (right workout ready, one-tap logging), flexibility (change it in a sentence), progressive + tailored training, coach check-ins.
- **Central finding / hypothesis:** the coach almost always gives in to what Thom wants that day (pump over rehab). Giving in is often right (he trained instead of skipping); the question is when to hold the line. Plan: write the policy down, then evals under pushback; RL only if prompting fails (no reward signal at n=1).
- **Thom writes the paper and docs.** Claude gives bullets in chat, never drafted prose (he stopped a prose fill on 10-20).
- **Evals: notes before rubric.** Per assistant reply: coaching 👍/👎, tools 👍/👎, 🌱 organic (a test chat can turn into real coaching midway), free note. The rubric should come out of the notes.
- **Data in a public repo is fine** (Thom, 10-20).

## Where it stopped
- **Branch `coaching-evals`: local only, not pushed.** Folder `coaching-evals/`: `traces.jsonl` (28 chats: 16 claude.ai + 12 Claude Code, labeled), `viewer.html` + `serve.py`, `completed.json` (17 completed workouts, snapshot 10-20), `export_claude_code.py`. `notes.json` (Thom's reviews, in progress) is **uncommitted**.
- **Thom is deleting stray completed copies** of `back-tri-pump-oct-10`: `13-oct-11:37-back--au2t`, `13-oct-11:52-back--ae49`, and (suggested) `10-oct-14:06-back--fqox`, the one the viewer wrongly matches. Then: re-pull `completed.json` (`recent_completed` limit 200 via the connector) and tick the line in #53. `kem6` is the real Oct 10 session (fixed to 26/26 sets).
- **Open questions:** Thom's baseline gym frequency before WILO; is the claude.ai export complete (nothing Sep 24 to Oct 9); should a chat note like "test, not real coaching" count as reviewed in the coverage circle; move #53 to Next?
- **Data limits:** the claude.ai export has no per-message times and only summaries of workout tool args (not full exercises).
- A Claude Doc duplicate of the paper outline exists (claude.ai artifact `8d76eb61…`, has some Claude prose). Delete it?

## Outside the repo
- `~/Downloads`: `coaching_traces.jsonl` (claude.ai export, the source), `*_claude_code.jsonl`, `*_all.jsonl`, `*_labeled.jsonl`, `*_coaching_only.jsonl`, `trace-viewer.html` (throwaway first viewer).
- Kaggle detour (10-17): `~/kaggle/gemma4-agent`. Gemma 4 Developer Agent competition; official starter = `ryanholbrook/getting-started-gemma-4-developer-agent`, run on Kaggle's free L4x4. Separate from WILO.

## Next
- Thom: review chats in the viewer (`python3 coaching-evals/serve.py` → http://127.0.0.1:8765/viewer.html), commit `notes.json`.
- Push `coaching-evals`; merge #92.
- #77 before inviting Lijon; #89 write-up feeds #84 and #81; #93 video this week.
- After enough notes: group them into patterns → rubric → LLM judge checked against Thom's thumbs.

## PRs and issues
- #90 / #91: tracker loads the earliest uncompleted assigned workout (merged; Oct 19 shoulder rehab loaded and was done).
- #92: paper outline in bullets, `docs/paper-llm-coaching.md` (open).
- #89: Thom's experience write-up. #93: demo video. #53: renamed "Fix how we maintain data" (stray copies, overwritten finish times, stale plans, no delete tool).
