# Model Evaluation & Improvement Plan
*2026-08-19*

## Goal

Find the best small model for a self-hosted AI product. Collect real usage data, then use it to make the model better via fine-tuning or RAG.

## Phase 1: Evaluate

Build a tool that fires the same prompt at multiple Ollama models simultaneously, displays all responses, and logs ratings.

**Models to test:**
- `qwen2.5:1.5b`
- `qwen2.5:3b`
- `phi3.5`
- others as discovered

**What to log per request:**
- timestamp
- prompt
- model
- response
- rating (1-5)

Output: `conversations.csv` — this is the raw dataset everything else builds on.

## Phase 2: Identify Weaknesses

After a few weeks of rated conversations, look at the data:
- Which model scores highest on average?
- What types of questions does each model fail at?
- Are there patterns in the low-rated responses?

## Phase 3: Fix It

Two options depending on what the data shows:

**Fine-tuning** — if the model consistently fails in a specific way (wrong tone, wrong domain knowledge, bad format), take the high-rated responses and fine-tune on them. Tools: Unsloth or TRL.

**RAG (Retrieval Augmented Generation)** — if the model lacks specific knowledge (your product docs, domain info, personal context), build a retrieval layer that injects relevant context into the prompt before sending to the model. No training required, faster to set up.

Likely both — RAG for knowledge gaps, fine-tune for style/behavior.

## What to Build

1. `eval.py` — multi-model evaluator with logging (write yourself)
2. `log.py` — single model conversation logger (write yourself)
3. Analysis notebook once data is collected
4. Fine-tune or RAG pipeline once weaknesses are identified
