# 2026-11-13: landing page beats, the willow, and Talk to Wilo

All on `feat/landing-beats` (PR #161, not merged). Preview: https://wilo2-1ee44--dev-6wjxhiwt.web.app/landing.html.
Earlier in the day: PR #159 (‹ › through past days on the day page) and #160 (Train button back to the tracker)
merged and live; hiwilo.com bought on Namecheap, DNS set, Firebase verification pending (and the domain still
needs adding to Auth authorized domains); `~/.local/bin/clip-sync` keeps primary selection and clipboard in sync.

## Where the page is now (PR #161)

Top to bottom:

- **Header:** WILO logo + "Talk to Wilo" button. Nothing else.
- **Hero:** "Wilo, because no plan survives contact with **reality**." The last word gets a red hand-drawn pen
  stroke, crumples away and is replaced: reality → the gym → my knee → reality. Then (desktop only) Thom's three
  lines (leg press occupied / slept on your shoulder funny / gym crush, "Bro, WE GOT YOU!") and the buttons.
  Lede: "Wilo, like the willow. It bends in the strongest winds and doesn't break." Phone: "Leg press is taken."
  → "No worries. Do hack squats first and I'll move leg press to 3rd." → the two swap order.
- **1 · The start:** "Two minutes from your old tracker to today's workout." Import 214 workouts, the coach asks
  what to account for (left knee, 3 days a week), plan in Review, Train, first set ticked. ~17 s; Thom: 17 s to a
  whole plan is the selling point.
- **2 · Progress:** "The work is working. Wilo helps you see it." + "Progress is easy to miss and easy to doubt.
  Wilo catches every PR, so you know your effort is paying off." Gold cell, toast ending "3rd PR this month", fireworks.
- **3 · Flow:** "A great workout is flow, not data entry." + "Tell your coach what's up. Wilo bends the plan, and
  your tracker keeps up." Phone: cranky shoulder → Landmine Press.
- **4 · Review, plan, repeat:** "Like shampoo, but for gains." Five lines light up with the weekly chat (incl.
  "Did you look back over last week?"), then Train, first Bench set ticked.
- **Closing screen, "Why it's called Wilo":** the oak and the willow, the dog, 52-year-old Westside powerlifter,
  "Every rigid plan I ever followed eventually broke me. Wilo is the plan that bends." — Thom, + Talk to Wilo.
  Footer lives inside it: App · Built in the open on GitHub →.
- Cut: the "How we got you" heading and nav item; Plan, Mid-workout, Form checks, For lifters/coaches, Read
  sections (copy kept in the master doc).

**Phones (≤600px, desktop unchanged):** hero is just headline + willow line, then the phone. Each beat's copy sits
over the bottom of its phone on a dark fade; beat 4 shows only the lit line. Scroll snaps beat to beat (hero, 4
beats, closing screen); you control the pace, you just can't stop halfway. **All devices:** each phone's animation
starts when it scrolls into view and restarts from the top when you come back.

## Decisions and why

- **Willow is the frame, not every beat.** Hero explains the name; beat 3 gets one nod ("bends the plan"); the oak
  story is the closer. Tone is storm, not spa: "flexibility" stays, "hope and compassion" stay off the page.
- **Let the reader do the work.** Thom: good writing paints the picture and trusts the leap. Dropped "Neither does
  your training" after the willow line, and "you stay in the workout" from beat 3.
- **Overlap between hero and beats is wanted.** Hero says why to care, beats show how. Don't police it.
- **Don't trash other trackers.** Be negative about the pain the reader has lived ("not data entry"), not about
  competitors. One line of contrast at most, and the founder note is the place for it.
- **The first ask is Talk to Wilo, not an email form or sign-in.** The chat is the product; sign-in comes after
  Wilo has proposed a week ("Want this in your tracker?"). #162 rewritten around it; build is #165.
- **Sell the dream.** Import (beat 1, "two minutes") and the PR count (beat 2, #163) don't exist yet. Fine for a
  demand test; build them first if the test pulls.

## Open issues from today

- #162: split test, now measuring first message → plan reached → signed in.
- #163: PR list view (backs beat 2's "3rd PR this month").
- #164: sticky-phone mobile layout (one phone, copy scrolls over it). Build on its own branch off main after #161
  merges and compare with the current overlay + snap.
- #165: Talk to Wilo on the landing page (Render endpoint, Haiku, turn cap, IP rate limit, kill switch, sign-in
  hand-off). Needs a visitor/intake section in coach.md, which Thom writes.

## Before #161 merges

- **"Talk to Wilo" (header and closing) goes to the Google sign-in screen** until #165 exists. Either ship #165
  first or rename the buttons back to "Open the app" for the merge.
- Thom to check on his actual phone: the pen stroke, the founder note, snap feel in iOS Safari, and whether the
  Coach button hidden under the copy on beats 3/4 matters.
- "Wilo is the plan that bends" in the founder note might be one willow too many; Thom's call.

## Also behind

- Master idea bank doc (https://claude.ai/artifact/72uQKd8wHPVE9LbD8G5ecb) is a few edits behind: beat 2 label
  ("2 · Progress"), beat 3 (Flow), the willow hero, the founder note, Talk to Wilo as the conversion.
- Still open from before: draft PR #158 (coach.md day mode, Thom's), verify the day tools on Render, the accidental
  artifact DMxq2RVTav1hhU489Vj7kx (delete?), PR #154 parked, local http server on 8001.

## Next

1. Thom writes the visitor part of coach.md (what Wilo asks a stranger with no history); then build #165.
2. Merge #161 (after the button decision above). hiwilo.com: Firebase verification, Auth domains.
3. #162 analytics (three funnel events + `?v=`), then a small paid round.

## Working-style note

Three times I built while Thom was still talking an idea through, and one of those edits (beat 3's "Your workout
changes…" line) landed even though he rejected it; I found and removed it later. Memory
`feedback_talk_before_build_copy`: "lets chat" / "keep talking" / "what do you got" means talk only; build when
he says build. Thom's offer of a hook that blocks edits in talk mode is still open.
