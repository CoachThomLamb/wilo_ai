# Small-model experiment: tool calling for Wilo

**Learning track** (Thom, 2026-10-28): fine-tune a small open model on RunPod to move one needle on a real WILO
task. The product stays on Claude (Opus) meanwhile.

**The needle: picking the right tool + arguments.** Given a real message ("did 3x8 at 135", "swap pull-ups"),
call the WILO tool Claude called, or none. Narrow and measurable, and what the papers say small models can win:
- arXiv 2512.15943: plain SFT (TRL, 1 epoch) of a 350M model beat ChatGPT on ToolBench (77.5% vs 26%).
- arXiv 2401.07324: small models fail when one model plans, calls tools *and* writes the reply. So the small
  model is the tool caller only; Claude stays the coach.

**Base model:** `Qwen/Qwen3.5-4B` (Apache 2.0). The same family has 0.8/2/9B, so the recipe compares across sizes.

## Files
- `build_eval.py` → `toolcall_eval.jsonl`: 95 real messages from Thom's chats (traces + tracker chats) with
  Claude's first tool call as a silver label. **Thom reviews:** fix `expected`, or put a note in `review`.
- `wilo_tools.json`: WILO's 15 tool definitions (same as Wilo uses), exported from `wilo/mcp_server.py`.
- `runpod/serve.yaml` + `runpod/pod.py`: serve the model with vLLM on a RunPod 4090 (`up` / `status` / `down`).
- `score.py`: run the eval against the pod (or Ollama) → right tool %, right tool + args %, per tool.
- `results/`, `.pod.json`: local, gitignored.

## Run the baseline
```bash
pip install -r ml/requirements.txt
export RUNPOD_API_KEY=...            # runpod.io → Settings → API Keys
python ml/runpod/pod.py up           # ~$0.70/hr from here
python ml/runpod/pod.py status       # waits for the model (first start downloads ~9 GB)
python ml/score.py --limit 10        # quick check, then without --limit
python ml/runpod/pod.py down         # stop paying
```

## Next
1. Thom reviews the labels. 2. Baseline (untrained Qwen3.5-4B). 3. Training data: the real messages + a few
hundred more generated in Thom's style. 4. LoRA with TRL on the pod. 5. Re-score against the baseline and Claude.
