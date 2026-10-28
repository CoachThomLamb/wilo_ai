#!/bin/bash
# Runs on the pod (vllm/vllm-openai image): train the LoRA, then serve the base model and the trained one side by
# side so ml/score.py can score both on ml/test.jsonl. Needs VLLM_KEY in the env. No SSH: the pod's start command
# downloads this branch and runs this script; follow it with the pod logs.
set -x
cd "$(dirname "$0")/../.."
export HF_HOME=/workspace/hf

# Training libs only; --no-deps keeps the image's transformers/torch, which vLLM needs.
pip install -q --no-deps trl peft && pip install -q datasets accelerate
python3 -c "import transformers, trl, peft, torch; print('versions', transformers.__version__, trl.__version__, peft.__version__, torch.__version__)"
python3 ml/train.py --out /workspace/out && echo TRAIN_OK || echo TRAIN_FAILED

ARGS="--max-model-len 16384 --gpu-memory-utilization 0.42 --api-key $VLLM_KEY --reasoning-parser qwen3
      --enable-auto-tool-choice --tool-call-parser qwen3_coder --language-model-only"
vllm serve Qwen/Qwen3.5-4B --port 8001 $ARGS &
sleep 180  # let the first one claim its memory before the second profiles the GPU
[ -d /workspace/out/merged ] && vllm serve /workspace/out/merged --served-model-name wilo-ft --port 8000 $ARGS &
wait
