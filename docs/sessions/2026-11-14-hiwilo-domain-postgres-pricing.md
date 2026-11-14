# 2026-11-14: hiwilo.com, Postgres idea, free tier plan (#166)

Short talk-only session, no code. Picks up from `2026-11-13-landing-page-willow.md`, which still holds the full
landing page state and the "Before #161 merges" list.

## hiwilo.com

Thom typed hiwilo.com into Google and it didn't go there. Checked: **https://hiwilo.com works** (serves Wilo,
http redirects to https). Likely causes:
- Typed into google.com's search box: the site is new and not indexed yet. Use the address bar; add the site to
  Google Search Console to get indexed.
- **www.hiwilo.com doesn't answer.** Fix: add it as a second custom domain in Firebase Hosting (redirect to
  hiwilo.com) and add the DNS record Firebase gives in Namecheap.
- Phone may have cached the old "not found"; try a private tab.

Still to do: add hiwilo.com to **Firebase Auth authorized domains** (sign-in will likely fail there until then).
Also `fe/` decides "on Hosting" with a `.web.app|.firebaseapp.com` regex, so on hiwilo.com authDomain falls back
to wilo2-1ee44.firebaseapp.com. Probably works, but fix alongside.

## Postgres (idea, not started)

Thom floated running our own Postgres as a monolith instead of Firebase. My take: **not now.** It doesn't help
the cold-traffic test (#162/#165), it's weeks with no user-visible change (incl. rebuilding the tracker's live
updates), and we'd own ops. Still on hold since 2026-10-06; keep app design DB-agnostic. Revisit when the paid
test shows demand, a feature is truly blocked by Firestore (relational queries like #163 are the likely one),
or the bill matters. Asked what's driving it; no answer yet.

## #166: free tier + paid coaching, capped token cost

Thom's plan, grounded in the #143 numbers. My pushback, in order:
1. Re-measure first (`scripts/token-cost/usage_report.py` + new Console CSV); the ~Nov 12 TODO is overdue and
   every cap/price depends on it.
2. #165 (anonymous Talk to Wilo) is the real uncapped cost exposure: hard caps belong there first.
3. Start with a 14-day no-card trial *or* a free tier, not both; the trial is one date check, the free allowance
   is metering + copy.
4. Price on value (~$15–30/mo plausible), not 3–5× cost; cost is the floor.
5. The free tier lists import + PR tracking, which don't exist yet.

Small: the goal line says "Willow" (should be Wilo); #166 isn't on project 5 yet (offered to add, no answer).

## Next

- Thom: decide on the #166 pushback; say whether to add it to the board.
- Firebase: www.hiwilo.com, Auth authorized domains, the hosting-check regex.
- Everything in the 2026-11-13 note's "Before #161 merges" and "Next" still stands.
