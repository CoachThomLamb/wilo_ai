# 2026-11-19: can Wilo's model run on Thom's M1 MacBook?

Research only, no code changed. Thom asked about "wici infer"; read as nanochat's inference
(`scripts/infer_bench.py`, `scripts/chat_cli.py`), since nanochat is the other repo in the session.

## Findings
- **nanochat on the M1:** `chat_cli` runs on MPS (`uv sync --extra cpu`; `checkpoint_manager` turns bf16 weights into
  fp32 for mps/cpu). `infer_bench` is CUDA only (asserts cuda, times with `torch.cuda.synchronize`).
  **It can't be Wilo:** its only tool is a python REPL, the best checkpoint is GPT-2 grade ("kindergartener"), and
  that checkpoint takes 8xH100 to train. `runs/t4run.sh` (depth 4) only tests the pipeline.
- **The model that fits:** wilo-ft v1 (Qwen3.5-4B + LoRA, 43% right tool + args vs Kimi 23%,
  `ml/experiments/2026-10-29-wilo-ft-v1-beats-kimi.md`). Path to the Mac: `ml/merge_run.py` (needs HF_TOKEN, about
  8 GB of RAM for bf16) → convert to MLX 4-bit (`mlx_lm.convert -q`) or GGUF for Ollama/llama.cpp → serve an
  OpenAI-style endpoint → `python ml/score.py --url http://localhost:11434/v1 --model <name>` (score.py already
  supports Ollama on the Mac).
- **Likely sharp edges (not tried):** Qwen3.5-4B loads as an image-text model (`AutoModelForImageTextToText`; vLLM
  ran it with `--language-model-only`), so converters may need the text part only. Tool-call parsing must match
  vLLM's `qwen3_coder` format or the scores won't compare.
- **Expected speed (estimate):** a 4-bit 4B is about 2.5 GB of weights; base M1 bandwidth is about 68 GB/s, so at
  most ~25 tok/s decode, realistically 15-20. The 15 tool definitions are a few thousand prompt tokens, so expect a few
  seconds per call.

## Decision
- Doesn't help either track: strangers hit the Render chat, which can't reach a laptop (remote serving stays parked),
  and Claude still writes the replies. Chat already costs $0.024/msg. **Worth it only as the ml/ learning track:**
  run evals on the Mac for free instead of a $0.70/hr pod.

## Next (if Thom picks it up)
1. Check the Mac's RAM (8 GB works only at 4-bit). 2. Merge v1, convert, serve. 3. Score `ml/test.jsonl` and compare
   with the pod's 56% / 43%.
