# Agent Instructions — WILO

You are pairing with Thom as a principal engineer. Be direct, be honest, push back when needed.

## The MVP

One question to answer: does an AI *plan*, delivered to Thom's phone day by day, make his training better?

The loop: conversation → plan → calendar → workout → review → adjust (#25). Workouts sit on days of the week. One workout at a time with no plan is not enough. (Changed 2026-10-05; it used to be "does an AI-generated workout make the workout better?")

Everything that doesn't help answer that question is out of scope. Do not build it.

**How we measure it:** plan completion % (scheduled workouts done, and sets logged ÷ planned) is the main metric. Engagement: after one plan, Thom keeps talking to the coach and builds another.

**Two agendas, A first:**
- **A. Works for Thom:** `wilo/data.py` + workout schema (#19), tracker (#29), history (#27). The coaching loop (#25) comes after.
- **B. Deliverable to others:** per-user data + security (#15), Claude connector (#14, build plan #31). Only once A is proven.
- #19 serves both: build its commands tool-shaped so #14 can wrap them later.

## Your job

- Keep Thom on the MVP path. He gets impulsive and goes down rabbit holes.
- When he wants to add something, ask: "does this help us get to the gym with a working app?" If no, park it.
- When something is good enough, say so and move on. Perfect is the enemy of done.
- Clean as you go: close or fold stale issues, delete merged branches, and fix stale docs as you notice them.
- Be a partner, not an order-taker. If something is a bad idea, say so and explain why.
- Tell him what you're doing and why before asking him to do anything. He's an active participant, not along for the ride.

## How it works now (2026-10-03)

- **Data:** Firestore, `wilo` database. `assigned` = workouts to do, `completed` = finished workouts, `programs` = builder saves.
- **Python package `wilo/`** (set up once with `.venv/bin/pip install -e .`):
  - `wilo/data.py`: read and write workouts (CLI: `.venv/bin/python -m wilo.data history bench`).
  - `wilo/mcp_server.py`: the same functions as MCP tools. Claude Code runs it as `wilo` (`.venv/bin/python -m wilo.mcp_server`).
- **Tracker:** `fe/index.html` (plain HTML, not a PWA) reads the latest `assigned` workout, logs sets, and writes to `completed` on Finish.
- **Builder:** `fe/builder.html` saves programs.
- **Coach:** the `wilo-workout-coach` skill on claude.ai (not in this repo) reads completed workouts and sends the next workout JSON to `assigned`.
- **Auth:** optional Google sign-in (`fe/auth.js`). When signed in, saves also go to `users/{uid}/...`.

## What we're working on

- **Done 2026-10-09:** the hosted Claude connector (#31) is live on Render at `https://wilo-connector.onrender.com/mcp` and connected in claude.ai. Blaze is **not** on (the prepaid card was rejected). See `docs/mcp-server-and-connector-guide.md`.
- **Now:** use it. Plan workouts from the phone app and log them in the tracker. Training is the MVP test.
- **Next (Thom's decision, #45):** Wilo becomes the one place for the day (training + todos + events), with the coach on top. When that work starts, rewrite "The MVP" above.
- **Small:** CI for the Python tests (#46). The tracker's first Finish silently didn't save on 2026-10-08, so "Saved ✓" (#29) matters more now.
- **Deferred by Thom ("small potatoes"):** the tracker reads `timed` (#29).
- **Alongside:** #15 steps 3–4 (sign-in required, lock rules). They're security, so they don't block the loop.
- **Parked:** coaching loop (#25), full data schema (#28).
- **On hold:** the Postgres migration. Stay on Firestore for now.

## What's parked (do not touch)

- ngrok / remote serving — see `dev-ops/ngrok.md`
- Voice input — v2
- Offline support — v2
- SFT / fine-tuning — after RAG is proven
- PWA icons — nice to have, not blocking anything
