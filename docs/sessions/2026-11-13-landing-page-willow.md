# 2026-11-13: landing page beats, the master idea bank, and the willow

All on `feat/landing-beats` (PR #161, not merged). Preview: https://wilo2-1ee44--dev-6wjxhiwt.web.app/landing.html.
Earlier in the day: PR #159 (‹ › through past days on the day page) and #160 (Train button back to the tracker)
merged and live; hiwilo.com bought on Namecheap, DNS set, Firebase verification pending (and the domain still
needs adding to Auth authorized domains); `~/.local/bin/clip-sync` keeps primary selection and clipboard in sync.

## Where the page is now (PR #161)

Hero plus four beats, each a phone that loops beside the copy. Everything else (Plan, Mid-workout, Form checks,
For lifters / For coaches, Read) is cut; the copy is kept in the master doc (below).

- **Hero:** "Wilo, because no plan survives contact with reality." Three lines (leg press occupied / slept on your
  shoulder funny / gym crush, "Bro, WE GOT YOU!"), then "Wilo helps you adapt your training to life, and keeps you
  on track at the same time." Phone: "Leg press is taken." → coach does hack squats first, moves leg press to 3rd.
- **1 · The start:** "Two minutes from your old tracker to today's workout." Import 214 workouts, the coach asks
  what to account for (left knee, 3 days a week), the plan lands in Review, Train, first set ticked. ~17 s a loop;
  Thom: 17 s to a whole plan is the selling point, don't trim it.
- **2 · Progress:** "The work is working. Wilo helps you see it." Set 3 goes 8→10, gold cell, PR toast ending
  "3rd PR this month", fireworks.
- **3 · Hurting:** headline still "Hurting? Wilo adjusts." with "A great workout is flow. When the plan changes,
  Wilo keeps you in it, and your tracker updates in real time." **Being rewritten** (see below).
- **4 · Review, plan, repeat:** "Like shampoo, but for gains." Five lines light up as the chat says them; the coach
  asks "Did you look back over last week?" before planning; then › to next Friday, tap Train, first Bench set ticked.
  The loop closes: review happens away from the gym, then you go back in.
- Signing out of the tracker now goes to the landing page.

## The master idea bank (Claude Doc)

https://claude.ai/artifact/72uQKd8wHPVE9LbD8G5ecb. Every headline, beat and section we tried, word for word, with
why it changed, plus five variants to split-test (#162). **Rule:** new ideas go in the doc as variants; the live page
changes when Thom says so. The doc is slightly behind the page (Docs service timed out): beat 3's line and the beat 2
label ("2 · Progress") still need updating there.

## Decisions and why

- **Four beats, not three.** Review/plan/repeat is one beat, because the review is its own moment away from the gym.
- **Sell the dream.** Import (beat 1, "two minutes") and the PR count (beat 2, "3rd PR this month", #163) don't exist
  yet. Fine for a demand test; paid traffic goes to an early-access signup, not the app. If the test pulls signups,
  build those two first.
- **Overlap between hero and beat 3 is wanted.** Hero says why to care; beats show how. People need telling twice.
  Don't police it.
- **Headline went from "Love training, tracking not so much?" to the reality line** on Thom's call, not via a test.
  The old one is in the doc as a variant.
- **Beat 2's feeling:** Wilo exists so people see they're getting better because of their effort; it's easy to get
  discouraged. "The work is working" puts the credit on them.
- **Beat 3's feeling:** a great workout is flow; you shouldn't have to switch context to data entry when the plan
  changes. Thom's lead line: **"A great workout is flow, not data entry."** (not on the page yet).

## The willow (the inflection point, end of session)

Wilo is named for the willow: it bends in the strongest winds and doesn't break. It's also Thom's dog's name;
someone once told him "you're an oak, you need a willow in your life to teach you that hope, compassion and
flexibility are signs of strength." Thom thinks this may be the metaphor for the whole page. Agreed, with limits:

- **Willow is the frame, not every beat.** Hero carries "Wilo, like the willow. It bends in the strongest winds.
  So does your training." (say the Wilo/willow link out loud once; nobody gets it from the spelling). Beats stay
  concrete. Beat 2 (progress) has nothing to do with bending; don't force it.
- **Tone: storm, not spa.** "Bends and doesn't break" is a strength claim. Keep "flexibility", drop "hope and
  compassion" from the page.
- **The oak story is the founder note** at the bottom (where the signup also needs to go): Thom was the oak, rigid
  plans broke him, Wilo is the plan that bends. Draft in the conversation; a photo of the dog would do more than
  copy, but it's personal, Thom's call. "Wilo bends so you don't break" is a possible headline variant to test later.

## Where it stopped

Mid-conversation on beat 3's supporting line. Candidates: "Tell your coach what's up. Wilo bends the plan. You stay
in flow." / "A good plan bends. A good coach adapts. Most trackers leave you to do the work when things change. Wilo
does it for you." Kicker would become "3 · Flow". Nothing built yet; Thom wants to talk it through first.

## Next

1. Finish beat 3 (lead line + supporting line + kicker), then the willow line in the hero, then the founder note +
   early-access signup at the bottom (the page currently ends on beat 4 with no call to action).
2. Update the master doc (beat 2 label, beat 3 line, the willow section).
3. Thom merges #161 when happy. hiwilo.com: wait for Firebase verification, add to Auth domains.
4. #162 split test: signup form ("What do you track with now?"), `?v=` variants with analytics.
5. #163 PR list (Backlog). Still open from earlier: draft PR #158 (coach.md day mode, Thom's), verify the day tools
   on Render, the accidental artifact DMxq2RVTav1hhU489Vj7kx (delete?), PR #154 parked, local http server on 8001.

## Working-style note

Three times today I built or committed while Thom was still talking an idea through. Saved as memory
`feedback_talk_before_build_copy`: "lets chat" / "keep talking" / "what do you got" means talk only; edit when he
says build. Thom's offer of a hook that blocks edits in talk mode is still open.
