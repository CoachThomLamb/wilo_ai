# Builder Refactor PR Review — Issues to Fix

Branch: `data-structure-refactor-clean`

**Status:** Refactor complete. Data model flattened (no blocks layer), exId derivation standardized, migration script ready. Before merging, we're reviewing 8 issues identified in code review.

## HIGH PRIORITY

### 1. exId Derivation Mismatch ✅ FIXED
**Problem:** Three locations deriving exId differently.
- `makeExercise()`: `toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')`
- `restore()`: Was missing special char removal
- `migration_script`: Was missing special char removal

**Fix:** Standardized all three to: lowercase → replace whitespace with dash → remove non-alphanumeric.
**Commit:** 441b6fd

---

### 2. Firestore Document ID Collisions ✅ FIXED
**Problem:** Format `DD-mmm-HH:MM-XXXXX` (e.g., `27-sep-14:30-shoul`) is not unique.
- Two workouts at same time with same name → same doc ID → data overwrites

**Fix:** Appended a 4-char suffix, differentiated by source:
- Live writes (`fe/index.html`): random base36 (`Math.random().toString(36).slice(2,6)`) — no coordination needed.
- Migration script: deterministic `sha1(source_id)[:4]` — keeps re-runs idempotent (same source doc → same target ID).

Format becomes `DD-mmm-HH:MM-XXXXX-YYYY` (e.g., `27-sep-14:30-shoul-a3f2`).

---

### 3. Migration is Destructive Without Rollback ⏸ DEFERRED
**Problem:** Script deletes old documents after renaming. If write fails but delete succeeds, data is lost.

**Decision:** Accept the risk for now. Single user, one-time migration, and we're moving to Postgres soon-ish anyway — investing in Firestore migration safety isn't worth it. Revisit if we ever run this at multi-user scale.

---

### 4. Old localStorage Drafts Won't Load Correctly ✅ NON-ISSUE
**Original concern:** `restore()` doesn't strip old `blockId` fields — feared UI would try to group by nonexistent blocks.

**Reality:** Nothing in the refactored `index.html` reads `blockId`. Old drafts load with vestigial `blockId` fields as dead data; UI renders correctly. First state change triggers `queueSave()`, which overwrites localStorage with clean new-format data. Self-healing on first interaction.

**Action:** None needed.

---

## MEDIUM PRIORITY

### 5. Dead Code — `targetLabel()` Function
**Status:** Function still defined but not called anywhere after removing `target` field.

**Action:** Remove or keep for backwards-compat?

---

### 6. New Exercises Have Empty exId Until Name Entered
**Problem:** When you add an exercise, it has `exId: ''` until the name field is filled in and changed.

**Current behavior:**
- `makeExercise()` derives exId from name if not provided
- But name input happens after creation

**Risk:** If user adds exercise and crashes before typing name, exId stays empty.

**Decision needed:** Generate placeholder exId on creation, or accept the gap?

---

### 7. Swap Logic Fragility
**Problem:** Swapping exercises multiple times might lose the original state in `ex.original`.

**Current structure:**
- `ex.original`: stores the original exercise before swap
- `ex.swapped`: boolean flag
- Swap button replaces current with fallback, stores current in `original`

**Risk:** If you swap A→B→A, does `original` still point to the real A?

**Decision needed:** Test multi-swap behavior or add safeguards?

---

### 8. Silent Failures in Event Handlers
**Problem:** Click listeners find exercise by `instanceId`, but silently return if not found.

**Example:**
```javascript
const ex = state.exercises.find(e => e.instanceId === exId);
if (!ex) return;  // ← silent fail
```

**Risk:** Bugs in instanceId generation/tracking are invisible at runtime.

**Decision needed:** Add console warnings, throw errors, or leave as-is?

---

## Next Steps

Working through issues 1-8 in order, making decisions on each before updating code.

Currently on: **#5 — Dead Code (`targetLabel()`)**

---

## Session Handoff (for resuming in a new session)

**Branch:** `data-structure-refactor-clean` (compare against `main`)

### Status of each issue
| # | Title | Status |
|---|---|---|
| 1 | exId Derivation Mismatch | ✅ Fixed (commit `441b6fd`) |
| 2 | Firestore Doc ID Collisions | ✅ Fixed (uncommitted, see below) |
| 3 | Destructive Migration | ⏸ Deferred (Postgres migration coming — not worth investing) |
| 4 | Old localStorage Drafts | ✅ Non-issue (self-heals on first autosave) |
| 5 | Dead `targetLabel()` | 🔜 Next up |
| 6 | Empty exId until name entered | Pending |
| 7 | Swap logic fragility | Pending |
| 8 | Silent failures in event handlers | Pending |

### Uncommitted changes (need commit before next session ideally)
- `fe/index.html` — added 4-char random base36 suffix to Firestore doc ID (line ~567); format is now `DD-mmm-HH:MM-XXXXX-YYYY`
- `migrate_firestore.py` — added `hashlib` import; `generate_doc_name()` now takes `source_id` and appends `sha1(source_id)[:4]` for deterministic idempotent re-runs; call site at line ~169 updated to pass `doc.id`
- `fe/PR_REVIEW.md` — untracked; this is the working doc

### Key decisions & context
- **#2 uniqueness strategy:** *random* for live writes (no coordination needed), *deterministic hash* for migration (idempotent re-runs). Not shared code — they're in different languages, but format spec is co-located in comments.
- **Prior migration data:** Thom will manually clean up existing migrated docs (old-format IDs without the `-YYYY` suffix) before any re-run. No cleanup logic needed in code.
- **Postgres migration** is planned "soon-ish" (mentioned 2026-09-30). Rationale for deferring #3. Saved to `~/.claude/projects/-home-thom-wilo/memory/project_postgres_migration.md`.
- **`fe/builder.html` is paused** — has stale format and still-nested blocks structure. Ignore during this refactor review. `fe/index.html` is the active file.
- **Single user right now** — inform risk tolerance. Migration safety, backwards-compat with drafts, etc., don't need heavy investment.

### Where to pick up
Start with **#5 (dead `targetLabel()`)**. Just verify no callers via `grep -rn "targetLabel" fe/` and either delete or confirm keep. Then walk through #6, #7, #8 the same way — decide first, edit second, always with Thom's sign-off before touching code (per `feedback_pair_dont_solo.md`).

### Working style reminders (from memory index)
- Small edits, terse "did X" note after each
- Show diff before/after non-trivial edits
- Don't silence command output
- Always confirm before code changes

