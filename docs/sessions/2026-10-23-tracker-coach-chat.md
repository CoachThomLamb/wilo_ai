# 2026-10-23: coach chat inside the tracker (phase 1)

## Decisions and why
- **Willow becomes the home of the coach.** Thom's pivot: chat with the coach inside the tracker instead of only through claude.ai, so we control the context and instructions and can build flows (plan, mid-workout, debrief) server-side. The claude.ai connector stays; both use the same tools and `wilo/data.py`.
- **Claude API first, not self-hosted inference.** Tool calling has to be reliable, and an always-on GPU costs ~$500/month (`docs/cost-of-self-hosted-ai.md`). A RunPod/vLLM backend can come later behind the same loop, scored with `coaching-evals`.
- **`/chat` lives in the connector server** (`wilo/chat.py`, routed from `make_server`). The tool list is read from the MCP server itself, so there is one set of tools. The uid comes from the verified Firebase ID token and reaches the tools via `mcp_server.CHAT_UID`; Claude never picks whose data it touches.
- **Only allowlisted uids can chat** (`WILO_CHAT_UIDS`, default Thom's uid from `config/wilo.json`), with a daily cap. It spends our API key, so it isn't open to every Google account that can sign in.
- **History is stored server-side and append-only** (`chat_threads/{id}/turns/*`, top-level so browsers can't touch it). The coach's context (date, profile) is frozen when a chat starts; the tracker starts a new chat each local day. Reason: replaying earlier turns byte for byte keeps prompt caching and thinking blocks valid.
- **Model `claude-opus-5-5`, effort `medium`, `fallbacks: "default"`.** Both are env-configurable (`WILO_CHAT_MODEL`, `WILO_CHAT_EFFORT`). A cheaper model for quick mid-workout questions is Thom's call once we see real costs in the `chat:` log lines.
- **Phase 1 keeps the existing dry-run flow in chat:** the coach shows what it would write and saves only after a "yes". Approve buttons are phase 2.

## What was built
- `wilo/chat.py`: `POST /chat` (CORS for the tracker hosts, PR previews and localhost), tool loop (max 12 model calls per message), refusal handling, per-user daily cap, usage log line.
- `wilo/mcp_server.py`: `CHAT_UID`; registers itself as `wilo.mcp_server` when run with `-m`, so `chat.py` gets the same module.
- `fe/chat.js` + `fe/index.html`: Coach button → full-screen chat sheet. It wakes Render when opened and suggests tapping Load after the coach saves a workout.
- `tests/test_chat.py`: 12 tests (100 total, all green).
- Tried locally in the browser at phone size: the real `/chat` app with a fake db, scripted Claude and stubbed token check, tracker on :8080 → server on :8000 (CORS, tool call, second message reusing the chat). **Not tried yet against the real Claude API or Firestore.**

## Where it stopped / next
- **To go live (Thom):** add `ANTHROPIC_API_KEY` in the Render dashboard (`wilo-connector` → Environment), merge, then try it on the phone. Without the key `/chat` answers 502 and nothing else breaks.
- Watch the `chat:` lines in the Render log for cost per message; adjust model/effort if needed.
- Phase 2: approve cards (dry-run diff → button), mid-workout and debrief modes (preload the current draft). Phase 3: browser voice (Web Speech API). Phase 4 (maybe): RunPod adapter.
- `.claude/instructions.md` still lists voice as parked (v2) and the coach as a claude.ai skill. Rewrite "How it works now" once the chat is in daily use.
