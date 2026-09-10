# Agent Idea: "Karpathy"
*2026-08-19*

## The Concept

An AI agent that teaches people how to use and build AI — in the style of Andrej Karpathy. First principles, build it from scratch, never hide the math, always make you type it out yourself.

## The Differentiator

Not a generic coding assistant. A specific persona: patient, curious, builds up from a single neuron. Explains the why, not just the what. Speaks to JS devs migrating to ML.

## The Knowledge Base

Thom's own notes, bugs, breakthroughs — the RAG assistant we're building becomes the curriculum. It knows the specific journey from JS dev → GPT from scratch → RunPod inference → fine-tuning.

## Connection to Existing Projects

- Extends "Karpathy for JS Bros" content series
- RAG assistant is the foundation
- Fine-tuned on real teaching conversations later
- Could become the YouTube series interactive companion

## Potential Use Cases

- Walk someone through building a neuron from scratch
- Debug their PyTorch code
- Explain what backprop is doing in plain English
- Help them get unstuck on RunPod / HuggingFace setup

## Next Steps (after RAG assistant is working)

- Define the persona more precisely
- Collect examples of good Karpathy-style explanations
- Use distillation (GPT-4o generating examples) to build training data
- Fine-tune Qwen on it
