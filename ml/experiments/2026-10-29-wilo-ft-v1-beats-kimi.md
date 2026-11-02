# wilo-ft v1: a 30-minute LoRA on Qwen3.5-4B beats Kimi on WILO tool calling (2026-10-29)

## Result (ml/test.jsonl, 51 real messages, first tool call only)

| model | right tool | right tool + args | median per item |
|---|---|---|---|
| **wilo-ft v1** (Qwen3.5-4B + LoRA) | 56% | **43%** | 1.5s |
| base Qwen3.5-4B | 35% | 33% | 5.9s |
| Kimi K3.1 Pro | 23% | 23% | 15.7s |

Per-item results: `ml/results/wilo-ft-20261029-0812.jsonl`, `Qwen-Qwen3.5-4B-20261029-0812.jsonl`,
`kimi-k3.1-pro-20261028-1619.jsonl`. The first run (lost with its pod, 2026-10-28) scored the same: 54% / 43%.

**Caveats:** labels are "what Claude did in the real chat", not what Thom would want. Scoring is first call only:
most of Kimi's misses are calling `coaching_method` first, which a multi-call scorer might accept.

## What's saved, and where

| what | where |
|---|---|
| code, prompt, test set, training data | git commit `ac01f2eba1f53db1ad039ebd49cc2206b9201eee` (branch `exp/toolcall-eval`, PR #125) |
| LoRA adapter, the exact training data, run settings | private HF repo `Successthom/wilo-toolcall`, folder `runs/20261029-120637/` |
| scores | `ml/results/` (committed) |

Training: `ml/train.py` defaults: 3 epochs, lr 1e-4, LoRA rank 16, 336 examples (300 synthetic `train_synth.jsonl`
+ 44 `seeds.jsonl`, minus summary-only labels). A40 48 GB (Secure, CA-MTL-1, $0.59/hr), ~30 min, ~$0.45.
Image `vllm/vllm-openai:v0.31.0`. Loss 5.5 → ~0.06.

## Reproduce

The prompt changed after this run (today's date was added on `exp/toolcall-data2`), so use the commit above.

- **Serve the saved model, no retraining:** pod start script `ml/runpod/serve_trained.sh` with
  `WILO_RUN=runs/20261029-120637` (without it, it takes the newest run). It merges the run and serves base on 8001
  and wilo-ft on 8000. Then `python ml/score.py --url https://<pod>-8000.proxy.runpod.net/v1
  --key <VLLM_KEY> --model wilo-ft --eval ml/test.jsonl`, at that commit.
- **Retrain from scratch:** pod start script `ml/runpod/train_and_serve.sh` with `HF_TOKEN` and `WILO_HF_REPO` set.
  Download the code by commit, not branch:
  `https://codeload.github.com/CoachThomLamb/wilo_ai/tar.gz/ac01f2eba1f53db1ad039ebd49cc2206b9201eee`.
  Pod setup details: `docs/sessions/2026-10-29-small-model-retrain.md` (RunPod lessons).
