# Builder Refactor PR Review — Issues to Fix

Branch: `data-structure-refactor-clean`

**Status:** All 8 issues resolved. Ready to merge.

## HIGH PRIORITY

### 1. exId Derivation Mismatch ✅ FIXED
**Commit:** 441b6fd — standardized all three to: lowercase → replace whitespace with dash → remove non-alphanumeric.
**Follow-up:** f8f89f5 — hoisted `deriveExId` to module scope; deduplicated 3 inline copies. Re-derives exId in the input handler on name change.

---

### 2. Firestore Document ID Collisions ✅ FIXED
**Commit:** 246357f — appended a 4-char suffix.
- Live writes: random base36 — no coordination needed.
- Migration: deterministic `sha1(source_id)[:4]` — idempotent re-runs.

Format: `DD-mmm-HH:MM-XXXXX-YYYY`

---

### 3. Migration is Destructive Without Rollback ⏸ DEFERRED
Single user, one-time migration, Postgres coming soon. Not worth investing in rollback.

---

### 4. Old localStorage Drafts Won't Load Correctly ✅ NON-ISSUE
Nothing reads `blockId`. Old drafts self-heal on first `queueSave()`.

---

## MEDIUM PRIORITY

### 5. Dead Code — `targetLabel()` ✅ FIXED
**Commit:** f8f89f5 — confirmed zero callers, deleted function.

---

### 6. New Exercises Have Empty exId Until Name Entered ✅ FIXED
**Commit:** f8f89f5 — input handler now re-derives exId via `deriveExId()` whenever the name field changes.

---

### 7. Swap Logic Fragility ✅ FIXED
**Actual bug found:** swap button was using array index (`data-swap="${e}"`) instead of instanceId — button was silently broken entirely.
**Commit:** f8f89f5 — fixed to `data-swap="${ex.instanceId}"`. Multi-swap A→B→A logic traced and confirmed correct.

---

### 8. Silent Failures in Event Handlers ✅ FIXED
**Commit:** f8f89f5 — all 5 handlers now `throw new Error('no exercise for id ' + id)` instead of silent return. Existing `window.onerror → note()` pipes errors to the on-screen status line.

---

## Bonus Cleanup (not in original review)

- **efd54cd** — Rewrote stale file header; deleted dead `.block-head` CSS; fixed reset comment; removed paranoid `typeof queueSave` guard.
- **120b2b1** — Removed legacy nested-blocks branch from `loadWorkout`. Verified via Firestore Admin SDK: all 7 `assigned` docs are flat, zero have `blocks[]`.
- **Separate commit** — Extracted `fetchLatestAssigned()` helper; deduped two near-identical Firestore load blocks (loadBtn + boot).

## Key Decisions

- **#2 uniqueness:** random for live writes, deterministic hash for migration. Different languages, co-located format comment.
- **#3 deferred:** Postgres migration coming soon-ish (noted 2026-09-30).
- **#7 swap:** A→B→A multi-swap works correctly once data attribute is fixed. Logged set values on the original survive swap round-trips (captured by reference).
- **Legacy blocks:** kept as defensive fallback until confirmed dead via Firestore query; then removed.
