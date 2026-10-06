# Example: the workout schema (2026-10-06)

**Setting:** WILO, a Claude Code session. Thom and Claude were deciding what goes in a schema file for workouts (#19, #28).
**Outcome:** Thom kept pushing back, and each pushback narrowed the problem until the real disagreement surfaced. Claude was writing a **contract** (what won't break the current software). Thom wanted a **model** (what a workout, exercise and set *mean* to a human).

## How it went

### 1. Claude over-built
Claude drafted a full JSON Schema: `profile`, `plan`, `workout`, `exercise`, `set` and `review`, strict (`additionalProperties: false`), with invented examples. At that point there were 0 plans, 0 profiles and 1 review.

> **Thom:** so this is premature - .... we don't need this yet. Also its limiting .... hmmmm YAGNI ? do you know that principle ? I mean its tricky bc we want to lift shit out of the agent part of the loop but ya . I want to do that iteratively, and I feel like this is trying to predict too much when we don't have enought data yet

Claude agreed and split it up: the workout shape had real data (24 docs), and the rest was prediction. Claude proposed shrinking to workout-only.

### 2. Claude moved ahead before the decision was made
> **Thom:** ok workout shape should be informed from assigned and completed right ? those are the workouts as of now.

Claude took that as a go-ahead and rewrote the file.

> **Thom:** slow down
> **Thom:** k we are still trying to figurre out what to do don't get carried away

### 3. Reset to the actual goal
> **Thom:** I really want to get a script up that reads and writes workouts from firebase that we can use from claude bc that is something we want to do and we don't have it yet

#19 was rewritten to cover only that: a schema plus a script, decoupled. The coaching loop and principles were taken out of it.

### 4. Pushback on noise
Claude built the schema from a field census ("required = present in every doc").

> **Thom:** ok I still am like why are we making all these extra data objects like workout .... we have the shape of assigned and completed - and your adding all this extra shit in here ? why - like its working the way I made it dont just agree with me but like what are all these extra feilds and mapping shit around it seems like overkill ?

Claude explained that every field exists in the data, and that "workout/exercise/set" are labels for the existing nesting, not new objects. It conceded that `$defs`/`$ref` was ceremony.

> **Thom:** ok so what is this refs defs shit ?
> **Thom:** nope take it out
> **Thom:** ok wait put it back in
> **Thom:** ok tell me what we are trying to accomplish with this schema file ?

Claude: one job, to stop a bad workout from reaching the phone. Second job: the coach reads it.

> **Thom:** ok but your adding a loooooot of extra fields that are not required and its creating cognitive noise for me. and I dont see the value in them so justify your choices or remove the extra shit especially the patterns ? what the fuck is that ?

Claude justified each field and found its own rule was wrong: the tracker fills in defaults for most "required" fields. It proposed cutting the schema to what the tracker truly needs.

### 5. The real disagreement surfaces
> **Thom:** ok we are looking at this in two fundamentally different ways. You are trying to write a contract to not break current software and data. I am trying to extract what semantically a workout, exercise and set need to have for them to be useful information for a human.

Every earlier round had been arguing about fields while the two of them were answering different questions. Claude's fields (`instanceId`, `swapped`, `fallback`, `pattern`) were implementation details. Thom wanted the domain: what makes a set, an exercise and a workout meaningful.

## What the drag signalled
| Thom's drag | What it pointed at |
|---|---|
| "premature… YAGNI" | Designing ahead of the data |
| "slow down" / "don't get carried away" | Acting before the decision was made |
| "what is this refs defs shit" | Machinery the reader doesn't need |
| "what are we trying to accomplish" | Purpose unclear, so fields couldn't be judged |
| "justify or remove… patterns?" | Implementation detail shown as meaning |
| "two fundamentally different ways" | **Root cause: contract vs. model** |

**Lesson:** repeated friction over details usually means the two sides disagree about the *goal*. Stop changing the artifact and ask what it's for, and from whose point of view.
