# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MVP Focus

One question to answer: **does an AI-generated workout delivered to a phone make the workout better?**

Everything that doesn't help answer that is out of scope. Don't build it. Keep Thom on the MVP path — when something is good enough, say so and move on.

What's parked (do not touch): ngrok/remote serving, voice input, offline support, SFT/fine-tuning, PWA icons.


## Static index.html tracker dev

Source of truth: `fe/index.html`

```bash
cd fe
python3 -m http.server 8080
```

Open `http://<local-ip>:8080/index.html` on phone (same WiFi).

## Firebase deploy

Copy from source to deployment dir, then deploy:

```bash
cp fe/index.html public/index.html
firebase deploy --only hosting   # deploys public/ to project wilo2-1ee44
```

## Architecture

**Static html file** (`fe/index.html`):
- Single-file, zero-server html with embedded js and css
- Source of truth for the tracker
- Deployed to Firebase Hosting via `public/index.html`


## Workflow

- **Write the issue first.** Before coding on anything non-trivial, write a short issue definition (goal, scope, non-goals) so Thom stays on the actual objective and doesn't drift. Ask if it's unclear.
- **Respect gitflow.** Feature work goes on a branch → PR → merge to main. Do not deploy to Firebase from a working branch or from local uncommitted state. Uncontrolled deploys have caused problems before.

## What's next (in order)

1. Clean up and land the builder PR.
2. **Parked — wait for green light before touching:** simplify the program/session JSON by removing the `program` and `blocks` wrapper levels (currently `{ program, sessions: [{ blocks: [{ exercises }] }] }`). The builder only ever uses one session and one implicit block, so most of that nesting is dead weight.


## Skills

Skills are tracked in `skills-lock.json` and gitignored from `.agents/`. After a fresh clone:
#todo is this a good idea - shouldn't we version control your skills ? 


