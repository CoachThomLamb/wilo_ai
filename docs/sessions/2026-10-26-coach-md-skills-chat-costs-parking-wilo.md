# 2026-10-21 to 10-26: coach.md is Thom's draft, skills, chat costs, parking WILO for the job hunt

Follows `2026-10-23-tracker-coach-chat.md` (and `2026-10-21-midworkout-merge-and-docs-refresh.md`).

## Decisions and why
- **`wilo/coach.md` is the single source of the coach's instructions.** The tracker chat pastes it into the prompt, the
  connector serves it (`coaching_method`), the `wilo-coach` skill only says "load it". Thom's 10-22 draft is now the
  method (#104): keep it short, glossary, plan and can't-do-the-exercise flowcharts. Cranes 3x6 per side stays the
  fallback for every user.
- **The skill is a Claude-app-only workaround:** claude.ai distrusts instructions that arrive as tool results (10-16),
  a skill counts as the user's own. The tracker chat doesn't need it. Lijon onboarding choice still open: Claude app +
  skill (her plan) or tracker chat (`WILO_CHAT_UIDS`, Thom's API bill).
- **Eval notes → rules:** top patterns from `coaching-evals/notes.json`: too wordy, too many questions, separate
  planning from execution, point to the tracker, answer only what was asked (posted on #83).
- **Chat model stays Opus 5.5** (Thom, 10-25): tried Sonnet as default in #107, reverted. Routing by workflow parked.
  Cost estimate from the reviewed traces: ~$15-20/month at Thom's mid-October pace (caching already on; output is the
  main cost). `WILO_CHAT_EFFORT=low` is the cheap lever if needed.
- **Docs:** issues hold work, docs hold how things are now, session notes hold what happened, the board is the only
  status. Pre-WILO notes moved to `prior-art/notes/` (#106). Rest of that cleanup (status off instructions.md, new
  README, fold sign-in doc into the connector guide) not done.
- **Firestore is the source; local exports are gitignored** (#112).
- **Hevy imports go in `completed`**, tagged `source: "hevy"` (the coach's history tools only read `completed`).
- **PR previews on one fixed URL** (#115/#116) so auth works without registering each preview.
- Onboarding (New User flow) tested end to end in the tracker chat on 10-24: works. Thom's profile now exists; it was
  empty before, which is why the coach called him new.

## Where it stopped
- **Thom is switching to job hunting** and wants the same approach there (goal + metric, files in a private repo,
  Claude skills, session notes). WILO is parked, not dropped; the write-up (#89), paper (#84) and demo video (#93) are
  portfolio material.
- Open PRs: #107 (1h cache on the chat's fixed prefix, log cache writes), #116 (fixed dev preview URL), #117 (tracker
  chats in the eval viewer), #118 (Hevy CSV import), #98 (old session note), #88 (stale instructions draft).
- `#107`: cache test (wait 10 min, second message should show `read` ~3,000+) can only pass after merge.

## Outside the repo
- **Google OAuth web client:** register the dev preview host once: origin `https://wilo2-1ee44--dev-6wjxhiwt.web.app`,
  redirect `https://wilo2-1ee44--dev-6wjxhiwt.web.app/__/auth/handler`. Then merge #116.
- **Render env (wilo-connector):** `ANTHROPIC_API_KEY` set; `WILO_CHAT_UIDS` = Thom + test account (raw uids,
  comma-separated, no quotes); `WILO_CHAT_EFFORT` possibly set to `low`.
- `~/Downloads/wilo-coach.zip`: the skill for claude.ai (Settings → Capabilities → Skills), not uploaded yet.
- Laptop `.venv` misses `anthropic` since #105: `.venv/bin/pip install -e .` in `~/wilo`.
- Merged branches `coach-skill-83`, `coach-draft-docs`, `docs-prior-art`, `wilo-infra-skill` not deleted (permission
  blocked); delete from the PR pages.

## Next (when WILO resumes)
1. Merge #107, #116 (after registering the dev URL), #117, #118.
2. #77 new-user test, then Lijon.
3. First real runs: tracker chat export (#117), Hevy import on a real CSV (#118).

## PRs and issues
- #99 wilo-coach skill, #101 wilo-infra skill, #104 coach.md = Thom's draft, #106 old notes to prior-art: merged.
- #100 separate coach cue and client note per exercise. #111 Hevy import. #112 tracker chats in the viewer (context
  trace parked there). #115 fixed dev preview URL. #83 coach flows checklist.
