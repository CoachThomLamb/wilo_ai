# WILO

Workout tracker hooked to an AI coach and a database, so Thom can manage his training.
Sessions run both locally and in the cloud (claude.ai / phone), so everything a session
needs to know must live in this repo.

## Project context

@.claude/instructions.md
@.claude/memory.md

**Working on `wilo/` (data engine, MCP server, connector sign-in)?** Read `docs/mcp-server-and-connector-guide.md` first.

## Session notes

- **At the start:** read the newest file in `docs/sessions/` to see where the last session left off.
- **At the end:** write `docs/sessions/YYYY-MM-DD-<topic>.md` and commit it on the working branch.
  Cover what was worked on, where it stopped, and what's next, plus open PRs/issues.
  Cloud sessions lose their disk when they end, so an uncommitted note is a lost note.
- **Focus on what git can't hold:** decisions and why, context from the conversation,
  where work stopped mid-thought, what's next, and things outside the repo (local backups, keys).
  Don't restate what git/GitHub already track (branch lists, SHAs, merge status).
  A one-line description per PR or issue is fine and helpful (e.g. "#27: migrate workout history").
