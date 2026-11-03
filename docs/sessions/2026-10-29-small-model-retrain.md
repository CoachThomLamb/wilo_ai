# 2026-10-29: small model retrained and saved; try-it tool

Follows `2026-10-28-small-model-experiment.md`. Branch `exp/toolcall-eval` (PR #125).

## What happened

- **The first fine-tuned model was lost** (pod terminated before saving). Thom: "moving forward PLEASE save the model
  output and the data". Now enforced in code: `ml/train.py` refuses to train without `--hub-repo` and uploads the adapter,
  the exact training data and `run.json` to the private HF repo `Successthom/wilo-toolcall` (`runs/<UTC time>/`), checks
  the weights landed, and exits `UPLOAD_FAILED` otherwise. `train_and_serve.sh` refuses to start without `HF_TOKEN` +
  `WILO_HF_REPO`. `ml/results/` is committed.
- **Retrained** on an A40 (Secure, CA-MTL-1, $0.59/hr; ~30 min training, ~$0.45 total). Saved as
  `runs/20261029-120637`. Loss 5.5 → ~0.06 over 3 epochs, 336 examples (300 synthetic + seeds).
- **Scores on `ml/test.jsonl` (51 items)**, reproducing the lost run:

  | | right tool | tool + args | per item |
  |---|---|---|---|
  | base Qwen3.5-4B | 35% | 33% | 5.9s |
  | wilo-ft | 56% | 43% | 1.5s |

  Weak spots: `update_workout` args 3/9 (picks the right tool 7/9), `exercise_history` 0/3, `coaching_method` 0/1,
  and `none` (answer without a tool) only 5/10.
- **Try it yourself:** `ml/merge_run.py` (rebuild a saved run from HF), `ml/runpod/serve_trained.sh` (pod start
  script: merge, then serve base on 8001 and wilo-ft on 8000), `ml/try.py` (type a message, see each model's tool call;
  nothing runs). First test: "add deadlifts to my todo for friday" → wilo-ft gave `due: 2026-11-13`: **the prompt has
  no today's date**, so it guesses dates. Fix in the next data round.

## RunPod lessons

- RunPod account **secret** `wilo_hf_write` holds the HF write token; pods use `HF_TOKEN={{ RUNPOD_SECRET_wilo_hf_write }}`.
  Claude can't create secrets (permission check); Thom ran `make_secret.py` himself.
- `vllm/vllm-openai` has **no git**: the start command downloads the branch tarball from codeload.github.com with
  python (repo is public). Start command used:
  `mkdir -p /workspace/wilo_ai && cd /workspace/wilo_ai && python3 -c "<urllib+tarfile extract of
  codeload .../tar.gz/refs/heads/exp/toolcall-eval>" && cd wilo_ai-* && bash ml/runpod/<script>.sh; sleep infinity`
- **`set -x` leaked the HF token into the pod logs** (fixed: tracing starts after the check, stops before the vLLM key).
- Pods were created via the RunPod MCP plugin (`create-pod`), not `pod.py`. A40 Secure had HIGH stock today.

## Where it stopped

- **Pod `zcnsapsjdjgyth` (wilo-try, A40, $0.59/hr) may still be running** for Thom to play with `try.py`.
  Terminate it when done (RunPod console, or ask Claude: `delete-pod zcnsapsjdjgyth`, then confirm with a read).
  Its vLLM key is throwaway and dies with the pod; it's in the local job tmp dir, not the repo.
- **Thom: rotate the HF write token** (`HF_model_storage` in `~/wilo/.env`): it appeared in pod logs and chat. Then
  update the RunPod secret `wilo_hf_write` with the new value.

## Next (ML track)

1. Put today's date (and weekday) in the prompt (`score.messages`) and in the synthetic data; retrain.
2. More / better data for `update_workout` args, `exercise_history`, and the no-tool case.
3. Score is first-call only; Kimi's low score was mostly "calls `coaching_method` first". Consider multi-call scoring.
4. Reminder: `.claude/instructions.md` parks SFT "after RAG is proven". This track is Thom's learning project
   (and job-hunt portfolio), not the MVP loop. Keep it from eating WILO time.

## Other open threads (outside this track)

- WILO: Thom merges #123 (chat per workout), then retarget #124 (Wilo knows the on-screen workout, warm-up on Load)
  to main. coach.md "how to use WILO" + in-workout reminders need Thom's list. PR #110 review is drafted at
  `~/Downloads/pr110-review.md` for Thom to post.
- Parked: per-turn context trace (#112), token cost / the high-usage external user (wilo-ops #13).
- Career (private `CoachThomLamb/career`): BMO AI Engineer due **Oct 29** (career #8, PDF ready in
  `~/career/resume/pdf/`), Startup Canada event Oct 29 (#5), BioRender contacts task (#7).
