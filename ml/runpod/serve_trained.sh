#!/bin/bash
# Runs on the pod (vllm/vllm-openai image): rebuild a saved run from the HF repo (ml/merge_run.py) and serve it as
# wilo-ft on port 8000, next to the base model on 8001, for ml/try.py or ml/score.py. No training.
# Needs HF_TOKEN, WILO_HF_REPO and VLLM_KEY; WILO_RUN picks a run (default: the newest).
cd "$(dirname "$0")/../.."
if [ -z "$HF_TOKEN" ] || [ -z "$WILO_HF_REPO" ] || [ -z "$VLLM_KEY" ]; then
  echo "SERVE_REFUSED: set HF_TOKEN, WILO_HF_REPO and VLLM_KEY"; exit 1
fi
export HF_HOME=/workspace/hf
pip install -q --no-deps peft && pip install -q accelerate huggingface_hub
python3 ml/merge_run.py --hub-repo "$WILO_HF_REPO" ${WILO_RUN:+--run "$WILO_RUN"} --out /workspace/out/merged || exit 1

ARGS="--max-model-len 16384 --gpu-memory-utilization 0.42 --api-key $VLLM_KEY --reasoning-parser qwen3
      --enable-auto-tool-choice --tool-call-parser qwen3_coder --language-model-only"
vllm serve Qwen/Qwen3.5-4B --port 8001 $ARGS &
sleep 180  # let the first one claim its memory before the second profiles the GPU
vllm serve /workspace/out/merged --served-model-name wilo-ft --port 8000 $ARGS &
wait
