# WILO Memory

## MVP Goal
Does an AI-generated workout improve the gym session? Nothing else matters yet.

## Status (2026-09-10)
- Step 1 ✅ — Finish export works on phone (`fe/sess_shoulder_lower_a-2026-09-10-0950.json`)
- Step 2 ⬜ — Paste session JSON into Claude on phone, get next workout JSON back
- Step 3 ⬜ — Take it to the gym

## Decisions
- No Qdrant, no admin agent — flat JSON files for now
- Session JSONs stay in git (small, versioned training data)
- `prior-art/` — old RunPod/Qwen experiments, keep for reference

## Structure
- `fe/tracker.html` — PWA, loads program JSON, exports session JSON on Finish
- `prior-art/runpod/` — Qwen inference + convo wrapper (Ollama)
- `prior-art/version_2/` — old Dockerfile + inference scripts
- `docs/` — specs, planning docs, dev-ops notes
