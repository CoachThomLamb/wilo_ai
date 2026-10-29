# 2026-10-28: small-model tool-calling experiment (+ Wilo chat work)

## Decisions and why
- **Learning track:** fine-tune a small open model to move one needle on a real WILO task. The product stays on
  Claude **Opus** (Thom killed model switching mid-workout: "I don't want the model to get dumber during a
  workout"; PR #121 closed). The old handoff's "moving to Haiku" is outdated.
- **Needle: picking the right tool + arguments.** The small model is the tool caller only; Claude stays the coach.
  Papers: arXiv 2512.15943 (plain SFT with TRL, 1 epoch, 350M model beat ChatGPT on ToolBench 77.5% vs 26%) and
  arXiv 2401.07324 (small models fail when one model plans + calls + replies → split roles).
- **Base model:** `Qwen/Qwen3.5-4B` (Apache 2.0). vLLM flags from its model card: `--reasoning-parser qwen3
  --enable-auto-tool-choice --tool-call-parser qwen3_coder --language-model-only`. Image `vllm/vllm-openai:v0.31.0`.
- **Synthetic data:** generate ~300 examples with Claude in a Claude Code session (no API cost) first; later redo
  with an open model on RunPod (e.g. Qwen3.5-27B on an A40, $0.59/hr) and compare which data trains better.
  Kimi K2 ruled out (needs a multi-GPU cluster). Note: Anthropic's terms restrict training *competing* models on
  Claude outputs; a private 4B tool-caller for WILO is fine; an open-model data path avoids the question if the
  model is ever released.
- **Training:** Hugging Face TRL `SFTTrainer` + LoRA on a 24 GB RunPod GPU (~15–30 min, < $1). Never train on the
  eval items: split the 95 into ~50 held-out test + ~45 seeds for generation.
- **24/7 serving cost** (live RunPod prices, 2026-10-28): a 16–24 GB pod is $0.16–0.25/hr ≈ $117–183/month;
  always-on serverless ≈ $423/month; scale-to-zero serverless ≈ $10/month at Thom's volume but cold starts.
  Breaks even with Opus (~$15–20/user/month) at ~7–12 users. Not worth it until fine-tuning proves out.

## What exists (branch `exp/toolcall-eval`, PR #125)
- `ml/build_eval.py` → `ml/toolcall_eval.jsonl`: 95 real messages from Thom's chats (claude.ai traces + tracker
  chats, Thom's uid only) with Claude's first WILO tool call or none (silver label; `review` field for Thom).
  Each item has `context` (6 earlier messages), `screen` (the on-screen workout + assigned doc id, like the app
  sends since #124; 61/95 have one), `expected` (`tool`, `args`, `args_complete`: false on 12 old claude.ai
  labels that kept only summaries).
- `ml/wilo_tools.json`: the 15 WILO tools (OpenAI function format), exported from `wilo/mcp_server.py`.
- `ml/score.py`: right tool %, right tool + args %, per tool, against any OpenAI-compatible endpoint (reads
  `ml/.pod.json`). Sends a User-Agent (RunPod's proxy 403s Python's default).
- `ml/runpod/serve.yaml` + `pod.py up|status|down`: tries 8 GPU types × Secure/Community until one is free. Needs
  `RUNPOD_API_KEY` in the shell. RunPod's Claude Code plugin is also installed and signed in (OAuth): pods can be
  created/terminated through its MCP tools without a key.
- Tracker-chat export (`coaching-evals/tracker_traces.jsonl`) is local and gitignored; regenerate with
  `coaching-evals/export_tracker_chats.py --uid <Thom's uid> --write` (PR #117).

## Results
- **Baseline (untrained Qwen3.5-4B, no on-screen workout): right tool 36% (35/95), right tool + args 32%
  (31/95)**, ~2 s/item on a 4090. It plays safe: reads (`recent_assigned`, `get_profile`) instead of acting;
  `update_workout` 1/18.
- **Baseline with the on-screen workout: right tool 32% (31/95), right tool + args 29% (28/95)**, ~4.4 s/item on an
  A4000. Knowing the workout made it *read* it instead of act: `update_workout` → `get_workout` 14/18 times
  (`get_workout` itself 3/3 now). So the gap is behaviour (act when the user says so), which is what SFT should fix.

## Where it stopped
- Both baselines done. Pod `mjyizzwyqy6qzc` terminated (list-pods empty); `ml/.pod.json` removed. No pods running.
  First boot on a fresh pod took ~25 min (vLLM image pull ~10 GB + model); a network volume or a template with
  the image cached would cut that for training runs.

## Next
1. Split the eval (~50 test / ~45 seeds); generate ~300 training examples in Thom's voice (see the prompt below).
2. `ml/train.py`: TRL SFTTrainer + LoRA; train on RunPod; serve the adapter with vLLM; re-score; compare with the
   baseline and Claude.

## Wilo chat work (same day, separate PRs, waiting on Thom)
- #123: one chat per workout (kept through Finish); merge first.
- #124 (stacked on #123): coach named "Wilo"; it knows the on-screen workout and where you are ([Tracker: …]
  line); workoutId saved on each chat; `/chat/warm` on Load. Retarget to `main` after #123 merges.
- Still to do: coach.md "how to use WILO" and in-workout "good workout" reminders (need Thom's list).

## Outside the repo
- RunPod plugin installed (user scope) and signed in.
- Career: BMO AI Engineer application due **Thu Oct 29** (career repo issue #8).
