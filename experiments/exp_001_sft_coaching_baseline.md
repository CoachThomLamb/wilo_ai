# Experiment 001 — SFT Coaching Baseline

## Hypothesis
Fine-tuning GPT-2 (starting from pretrained HuggingFace weights) on coaching-style conversation data will produce measurably better coaching responses than the pretrained baseline.

## Setup
- Model: GPT-2 (pretrained weights from HuggingFace)
- Starting point: pretrained weights, NOT trained from scratch
- Method: Supervised Fine-Tuning (SFT) only — strip out RL/RLHF portions of nanochat

## Steps

### 1. Baseline
- Load pretrained GPT-2 weights from HuggingFace via nanochat
- Run a coaching conversation (same prompt each time)
- Save the output as the baseline

### 2. SFT — Round 1
- Review the SFT training data in nanochat
- Run SFT on the pretrained weights
- Run the same coaching conversation prompt
- Save output as Post-SFT Round 1

### 3. Evaluate Round 1
- Compare baseline vs Post-SFT Round 1 responses
- Identify where the coaching conversation is still weak

### 4. SFT — Round 2
- Update the SFT training data to better reflect good coaching conversation style
- Either continue from Round 1 weights OR roll back to pretrained and retrain
- Run SFT again
- Run the same coaching conversation prompt
- Save output as Post-SFT Round 2

### 5. Compare
- Baseline vs Round 1 vs Round 2
- Document what changed in the data and what changed in the output

## Coaching Prompt (same across all runs)
```
User: I've been training for about a year. Here's my recent history: [workout data]. What should I focus on next?
```

## Success Criteria
- Post-SFT model gives more specific, structured, actionable coaching advice than the pretrained baseline
- Responses reference training history rather than giving generic answers

## Files
- `be/inf_1.ipynb` — inference notebook (RunPod)
- `be/` — model code (nanochat GPT-2 base)
- `experiments/` — results saved here per run
