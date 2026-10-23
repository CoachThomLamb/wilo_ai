# RAG Assistant — Spec
*2026-08-19*

## What It Does

Takes a question, searches your notes for relevant content, injects it into the prompt, sends to Ollama running on M1. Answers come from the model + your own knowledge base.

## Flow

```
user question
→ extract keywords
→ search docs folder for matching files
→ read matching files
→ build prompt: [system] + [retrieved context] + [user question]
→ POST to Ollama API
→ print response
→ loop
```

## Inputs

- User question (typed in terminal)
- Docs folder to search (start with `~/wilo/docs/`)

## Search Strategy (start simple)

Use Python's `pathlib` to walk the docs folder, read each `.md` file, check if any keywords from the question appear in the content. Return the top N matches.

No embeddings yet. Grep is fine to start.

```
keywords = question.lower().split()
score each file by how many keywords appear in it
return top 3 files
```

## Prompt Structure

```
SYSTEM: You are a personal assistant. Use the provided notes to answer questions. 
If the notes don't contain the answer, say so.

CONTEXT:
--- wilo/docs/runpod-deploy-reference.md ---
[file contents]

--- wilo/docs/model-eval-plan.md ---
[file contents]

USER: what was that thing we did to fix the HuggingFace disk error?
```

## Ollama API Call

POST to `http://localhost:11434/api/generate`

```json
{
  "model": "qwen2.5:3b",
  "prompt": "<full prompt string>",
  "stream": false
}
```

## Output

Print the model's response. Optionally log question + response + which files were retrieved to a CSV.

## Files

- `~/wilo/devops/rag.py` — the script
- `~/wilo/docs/` — knowledge base (add new .md files as you learn things)

## What to Build First

1. The search function — takes a question, returns list of matching file paths
2. The context builder — reads those files, formats them into a string
3. The Ollama call — sends the prompt, returns the response
4. The loop — keep asking questions until exit

## What to Add Later

- Search `~/.claude/memory/` as well
- Embeddings + vector search if keyword search misses too much
- File watcher that auto-indexes new docs
- Gradio UI instead of terminal
