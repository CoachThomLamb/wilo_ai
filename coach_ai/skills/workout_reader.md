---
name: wilo-workout-coach
description: Read Thom's finished WILO workouts from Firestore, check in with him, then build and post his next workout to the WILO programs collection. Use when a WILO session is logged (webhook) or when asked to plan the next WILO workout.
---

# WILO workout coach

Loop: a workout is finished in WILO -> read it and recent history from Firestore -> check in with Thom -> build the next workout -> write it to `programs` -> confirm.

## Firestore contract (current — do not change)

- Firebase project: `wilo2-1ee44`
- Database: `wilo` (named database, NOT `(default)` — every client/REST call must target it explicitly)
- REST base: `https://firestore.googleapis.com/v1/projects/wilo2-1ee44/databases/wilo/documents`
- Collections (top level, case-sensitive):
  - `sessions` — finished workouts. Read only.
  - `programs` — planned workouts. Claude creates new docs here. Never edit or delete existing docs unless Thom asks.
- Network: `firestore.googleapis.com` and `oauth2.googleapis.com` must be on the org's allowed domains.
- Auth: service account key (JSON) with scope `https://www.googleapis.com/auth/datastore`. The key is supplied at runtime; never commit it to this repo.

### Document shape (same for sessions and programs)

```json
{
  "program": { "id": "prog_<ms>", "name": "legs-sept-23" },
  "sessions": [
    {
      "id": "prog_<ms>",
      "name": "legs-sept-23",
      "blocks": [
        {
          "id": "blk_default", "name": "", "notes": "",
          "exercises": [
            {
              "id": "ex1-5mbe6",
              "name": "step up",
              "custom_name": "Risers",
              "timed": false,
              "swapped": false,
              "cue": "Right ham got twinged",
              "sets": [ { "reps": 6, "lbs": 35, "custom": "4", "done": true } ]
            }
          ]
        }
      ]
    }
  ],
  "finishedAt": "2026-09-24T10:31:01.973Z"
}
```

- Doc ID: `{program.id}-{timestamp_ms}` (e.g. `prog_1790181708707-1790245861973`). A finished session keeps its program's `program.id`, which links plan to actual.
- Exercise IDs: `ex<n>-<5 random chars>`.
- New planned workouts: every set `done: false`, `finishedAt: null`.
- Empty values may appear as `""` for `reps`/`lbs` (e.g. stretches). Handle them when reading; match the existing format when writing.

### The `custom` field — read carefully

- `custom_name` (exercise level) labels an extra quantifiable variable for that exercise. `custom` (set level) holds the value.
- It directly affects difficulty even though it isn't sets, reps or weight. Treat it as part of the load when analyzing progression.
- Examples:
  - Step up: `custom_name: "Risers"`, `custom: "3" | "4" | "5"` = riser/step height on an adjustable riser.
  - Dragging: `custom_name: "Direxrion"` (direction), `custom: "Pull" | "Drag"` = drag style. It's kept as one exercise for convenience.
- `custom_name: null` means no custom variable. Ignore `custom` then.

### Signals to read

- `done: false` sets in a finished session = skipped or bailed. Find out why.
- `cue` is free-text notes from Thom (pain, form, why he stopped). Always read these; they drive the check-in.

## Workflow

1. **Identify the trigger.** If a session doc ID was passed in (webhook/manual fire), read that doc from `sessions`. Otherwise read the most recent by `finishedAt`.
2. **Load history.** Read recent `sessions` (last ~2–4 weeks) and current `programs` for context. Compare each finished session with its program (same `program.id`) to see planned vs. actual.
3. **Analyze.**
   - Per exercise: volume, top load, `custom` value and trend, completion rate.
   - Pain or injury notes in `cue` (e.g. hamstring twinge), skipped exercises, sets not done.
   - Balance across sessions: legs vs. upper vs. cardio. Thom alternates strength and cardio days and keeps gym time short.
4. **Check in: stop and ask.** Send a short recap (2–4 lines) and 3–5 questions, for example:
   - How did anything flagged in cues feel since (soreness/pain, 0–10)?
   - Energy today? Time available?
   - What's next: legs, upper, cardio, recovery?
   - Anything to avoid or push?
   Wait for his reply. Do not build or write before he answers.
5. **Build the next workout.**
   - Progress conservatively from the last actual performance, not the plan.
   - Adjust around pain notes: lower load, swap the exercise, or drop it; say which.
   - Keep `custom` values meaningful (e.g. a riser height he has actually used).
   - Use a `cue` on each exercise for coaching notes (target, form focus, stop rule).
   - Show Thom the workout and get a yes before writing.
6. **Write to `programs`.** Create a new doc in the current format: new `prog_<now_ms>` ID, doc ID `{program.id}-{now_ms}`, all sets `done: false`, `finishedAt: null`. Create only; never overwrite.
7. **Confirm.** Reply with the doc ID, program name, and a one-line summary per exercise.

## Reference: REST access (Python)

```python
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

BASE = "https://firestore.googleapis.com/v1/projects/wilo2-1ee44/databases/wilo/documents"
creds = service_account.Credentials.from_service_account_file(
    KEY_PATH, scopes=["https://www.googleapis.com/auth/datastore"])
s = AuthorizedSession(creds)

def enc(v):  # Python -> Firestore value
    if v is None: return {"nullValue": None}
    if isinstance(v, bool): return {"booleanValue": v}
    if isinstance(v, int): return {"integerValue": str(v)}
    if isinstance(v, float): return {"doubleValue": v}
    if isinstance(v, str): return {"stringValue": v}
    if isinstance(v, list): return {"arrayValue": {"values": [enc(x) for x in v]}}
    if isinstance(v, dict): return {"mapValue": {"fields": {k: enc(x) for k, x in v.items()}}}

def dec(v):  # Firestore value -> Python
    if "mapValue" in v: return {k: dec(x) for k, x in v["mapValue"].get("fields", {}).items()}
    if "arrayValue" in v: return [dec(x) for x in v["arrayValue"].get("values", [])]
    if "integerValue" in v: return int(v["integerValue"])
    return next(iter(v.values()))

# read one session
doc = s.get(f"{BASE}/sessions/{doc_id}").json()
session = {k: dec(x) for k, x in doc["fields"].items()}

# recent sessions
q = {"structuredQuery": {"from": [{"collectionId": "sessions"}],
     "orderBy": [{"field": {"fieldPath": "finishedAt"}, "direction": "DESCENDING"}],
     "limit": 10}}
rows = s.post(f"{BASE}:runQuery", json=q).json()

# create a program (create-only via documentId)
s.post(f"{BASE}/programs", params={"documentId": new_doc_id},
       json={"fields": {k: enc(x) for k, x in program.items()}})
```

Dependencies: `pip install google-auth requests`.

## Enhancement backlog (not applied — current contract wins)

- Rename `custom_name` -> `custom_key` and set `custom` -> `custom_value`.
- Readable doc IDs: `YYYY-MM-DD-<slug>` instead of `prog_<ms>-<ms>`.
- Stable `exercise_key` slugs from an exercise catalog, for reliable progression tracking (names are free text today, e.g. trailing spaces).
- Use `null` instead of `""` for empty `reps`/`lbs`.
- Add `createdAt` and `createdBy: "claude"` on Claude-written programs.

## Status / open items

- Read and write verified against `wilo2-1ee44` / `wilo` on 2026-09-24.
- Test doc `programs/prog_1790267739791-1790267739791` (name `claude-test`): check it renders in WILO, then delete.
- Existing `programs` docs had `finishedAt` set (not null). Confirm WILO shows programs with `finishedAt: null`.
- Trigger: plan is a Cowork scheduled task fired by WILO when a session is saved (e.g. a Firestore onCreate Cloud Function on `sessions`), passing the session doc ID. Not yet confirmed that the task exposes an external webhook URL. Fallback: an hourly task that processes sessions it hasn't handled yet.
