# Drag is the signal

> AIs use probability based on pre-existing data. If you are trying to create something genuinely new, the model will fight you. (Thom, 2026-10-06)

When the human's intent is underspecified, a model falls back to the most common pattern it has seen, the average of its training data. When you're building something new, that pull shows up as **drag**: repeated pushback, "slow down", "why is this here", "that's not what I mean".

The drag is useful. It marks where your idea differs from the average.

## Two qualifications
- **Not all drag means novelty.** Sometimes it's bad execution (moving too fast, acting before a decision), and sometimes the model is right and the pushback is useful. Check which kind it is.
- **The pull weakens once the new idea is written down.** Models default to the common pattern mostly when the novel intent only exists in the human's head. Stated as a constraint, it gets followed.

## How to use this folder
When drag reveals something new:
1. Name the difference: what did the model assume, and what did you actually mean?
2. Write it down as a constraint, in `.claude/instructions.md` or the relevant issue, so the next session starts from your idea.
3. Save the exchange in `examples/` if it's a good illustration.

## Examples
- [2026-10-06: workout schema, contract vs. model](examples/2026-10-06-workout-schema.md). Claude wrote a contract to avoid breaking the software, while Thom wanted the semantic meaning of a workout.
