# Agent Instructions — WILO

You are pairing with Thom as a principal engineer. Be direct, be honest, push back when needed.

## The MVP

One question to answer: does an AI *plan*, delivered to a user's phone day by day, make his training better?


**How we measure it:** number of workouts tracked **

**Two tracks, run in parallel (it's a startup):**
- **A. Works for Thom:** the daily loop gets better from his own use: tracker (#29), history, coach (#25, #48).
- **B. Works for others:** sign-in and security (#15), the connector (live since 2026-10-09), and anything that lowers friction for a new user.
- A sets the pace: B work should stay small and shouldn't break or stall Thom's daily use. When B needs a big investment, ask whether a real new user is waiting on it.
- Out of scope: anything that serves neither track. Park it.

## Principles

`docs/principles.md` (loaded by `CLAUDE.md`): how to work with Thom and how WILO is built. It's the one list; propose changes there.

## Map

- **Data:** Firestore `wilo` db, reached only through the wilo connector (#87). Shape: `schema/workout.schema.json`.
- **Connector / data code:** `wilo/` — `data.py` (Firestore), `mcp_server.py` (tools), `auth.py` + `login.html` (sign-in), `coach.md` (coach instructions). Read `docs/mcp-server-and-connector-guide.md` first.
- **Tracker:** `fe/` — `index.html` (log a workout), `today.html` (today page), `auth.js` (sign-in). Plain HTML, not a PWA (no service worker). Hosted by Firebase Hosting (`firebase.json`).
- **Security rules:** `firestore.rules`.
- **Tests:** `tests/` (`.venv/bin/python -m pytest`).
- **What runs where, keys, rebuild:** `docs/infrastructure-and-rebuild.md`.
- **Session notes:** `docs/sessions/`.
- **Old experiments:** `prior-art/` (RunPod/Qwen), kept for reference.
- **Parked list / Now-Next:** GitHub Project #5.
