# WILO data schema (draft)

Draft for review (#19 step 3, designed against #25). This file defines the data shape for humans and the LLM. Once it's agreed, it becomes a machine-checkable schema that `wilo_data.py` validates against.

**Principles**
- Everything lives under `users/{uid}/...`.
- **Text first** for anything the coach reasons about (profile, plan, reviews). Use structured fields only where code or the tracker needs them.
- Workouts keep the shape the tracker reads and writes today. Changes are small and listed under "Tracker changes".

## Where things live

| Path | What | Written by |
|---|---|---|
| `users/{uid}/profile/current` | Who Thom is: lasting facts, preferences, standing rules | coach (from conversation) |
| `users/{uid}/plans/{planId}` | What he's working on now: goal, weekly layout, progression | coach |
| `users/{uid}/assigned/{docId}` | Planned workouts, one per scheduled day | coach |
| `users/{uid}/completed/{docId}` | What was actually done | tracker (Finish) |
| `users/{uid}/reviews/{reviewId}` | What happened and what changes, per workout and per week | coach |

## Profile: `users/{uid}/profile/current`
One doc. It outlasts plans, and the coach reads it at the start of every conversation.

```json
{
  "updatedAt": "2026-10-06T15:00:00Z",
  "facts": [
    "Right leg is the weak side: can't hold a basic crane on the right; single-leg curl R 9,6 vs L 10,10 (2026-10-06)",
    "Hernia: stop crunch-type work if it bulges or aches"
  ],
  "preferences": [
    "No cues on exercises",
    "Warm-up first (dragging), stretches right after. They get skipped when they come last"
  ],
  "rules": [
    "If the right-side crane fails, regress to basic cranes and skip step-ups"
  ],
  "schedule": { "daysPerWeek": 3, "minutesPerSession": 60 }
}
```
- `facts`, `preferences`, `rules`: plain-language lists. The coach adds and edits them, and Thom can read them.
- `schedule`: the only structured part. The values shown are placeholders until Thom sets them.

## Plan: `users/{uid}/plans/{planId}`
Open-ended. It lasts until it's changed in conversation. Only one plan is `active` at a time.

```json
{
  "id": "plan-2026-10-06-right-leg",
  "status": "active",
  "createdAt": "2026-10-06T15:00:00Z",
  "endedAt": null,
  "goal": "Bring the right leg up to the left; keep shoulders healthy",
  "reasoning": "Why the plan is built this way, in the coach's words",
  "week": [
    { "day": "Mon", "focus": "legs" },
    { "day": "Wed", "focus": "pull + press" },
    { "day": "Fri", "focus": "shoulders" }
  ],
  "progression": [
    "Progress only what was fully completed; repeat what wasn't",
    "Leg extension iso: 2 x 45s @ 115 before adding a third set"
  ]
}
```
- `week`: the default layout. The coach turns it into dated workouts one week at a time.
- `progression`: plain-language rules for this plan. Standing rules go in the profile.

## Workout: `assigned` and `completed`
One shape for both. `assigned` is the plan for a day, and `completed` is the same workout with what was logged.

```json
{
  "id": "prog_1791285116820",
  "name": "legs-oct-6",
  "planId": "plan-2026-10-06-right-leg",
  "scheduledFor": "2026-10-06",
  "assignedFor": "2026-10-06T11:11:56.820Z",
  "finishedAt": "2026-10-06T13:16:29.498Z",
  "exercises": [
    {
      "instanceId": "ex7-ab12c",
      "exId": "leg-extension",
      "name": "Leg extension",
      "timed": true,
      "custom_name": null,
      "cue": "",
      "note": "",
      "fallback": null,
      "swapped": false,
      "original": null,
      "sets": [
        { "lbs": 115, "reps": 45, "done": true, "custom": null }
      ]
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `id` | Workout ID. It's the same in `assigned` and the matching `completed` doc, which is how they link up. |
| `planId` | **New.** The plan this workout belongs to, or `null` for a one-off. |
| `scheduledFor` | **New.** The local date the workout is for (`YYYY-MM-DD`). The tracker uses it to find today's workout. |
| `assignedFor` | When the coach posted it. The name is misleading, but it stays for tracker compatibility. |
| `finishedAt` | `completed` only. Set by Finish. |
| `exId` | Stable exercise key across workouts (`step-up`, `dead-hang`). It's what links an exercise's history together. |
| `timed` | `true` means `reps` holds **seconds**. |
| `cue` | The coach's instruction. Empty by default, per Thom's preference. |
| `note` | **Thom's** note from the gym ("These are great"). |
| `custom_name` / `custom` | One free-text column per exercise. Conventions: `"Risers"` (step-up height), `"Side"` with `R`/`L`, `"Direction"` (`Drag`/`Pull`). If an exercise needs two values, use `R@3` or split it into two exercises. |
| `fallback` / `swapped` / `original` | An easier variant and the swap state. Unchanged. |
| `sets[].lbs` | Weight. Blank or `0` means bodyweight. **Allowed on timed sets** (weighted holds). |

## Review: `users/{uid}/reviews/{reviewId}`
Written by the coach after each workout and once a week.

```json
{
  "id": "review-06-oct-09:16-legs--9z50",
  "kind": "workout",
  "completedId": "06-oct-09:16-legs--9z50",
  "weekOf": null,
  "createdAt": "2026-10-06T15:30:00Z",
  "summary": "34/42 sets. Lunge stretch done 4/4 at #2. Step-ups skipped by rule.",
  "findings": [
    "Right leg weaker: no right-side crane; curls R 9,6 vs L 10,10",
    "Leg extension iso at 115 faded: 45s then 30s"
  ],
  "changes": [
    "Profile: add right-leg fact and the crane to step-up rule",
    "Next legs: 2 x 45s @ 115 leg extension; right side first on single-leg work"
  ]
}
```
- `kind`: `workout` (uses `completedId`) or `week` (uses `weekOf`, the Monday's date, and covers missed days and catch-up).
- `changes` records what the coach changed in the profile, plan or next week, so the "why" stays with the data.

## Tracker changes this implies (`fe/index.html`)
1. Read `timed` directly. Today it's only inferred from `target.duration_sec` (`:229`). Keep that as a fallback.
2. Show the lbs column on timed exercises too (`:290`), for weighted holds.
3. Finish writes Thom's note as `note`. Today it writes it as `cue` (`:517`), which mixes Thom's notes with coach cues.
4. Finish keeps `planId` and `scheduledFor` from the assigned workout.
5. Load picks the workout with `scheduledFor` = today, or the next upcoming one, plus a week strip (#25).

## Not decided yet
- Rename `assignedFor` to `postedAt`? That would mean a tracker change and a data migration. I'd say not now.
- Is `profile.schedule` worth having, or should the plan's `week` be enough?
- After a workout is completed, does the `assigned` doc stay as it is? I'd say yes, so planned vs done can be compared.
