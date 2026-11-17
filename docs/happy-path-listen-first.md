# The happy path: listen first, then tell

**Status:** draft. Notes from a conversation on 2026-11-14 between Thom and Claude (playing a startup advisor
deciding whether to invest), plus what an interview with user B added on 2026-11-16. Nothing here is decided. The coach wording belongs in `coach.md`, which Thom writes.

## The pipeline we want

Landing page → Talk to Wilo → track a workout → pay.

An investor wants to see one stranger go all the way through before anything else matters.

## Wilo in one sentence

> It tells you what to do and listens when you say what you're doing.

(Thom's words.) The mid-workout bend isn't a separate feature. It's both directions in the same minute: Wilo says
leg press, you say it's taken, Wilo says something else.

## What the data showed

A read-only look at coach chats and workouts on 2026-11-14. Besides Thom there are three users. All were asked
to try Wilo and onboarded by hand, so this is a tiny, friendly sample.

| User | Workouts logged | What they used the coach for |
|---|---|---|
| A | 26 | Building workouts on demand, logging after the fact, fixing tracker mistakes |
| B | 3 | Dictating their own workout as they did it, live in the gym. Stopped after three days (the interview says why, below) |
| C | 0 | An intake chat and one planned workout. Came back two days later, said hi, and left |

- **Nobody used the mid-workout bend.** We had assumed it was the "oh, this is different" moment.
- **Everybody tapped Coach.** The button isn't the problem.
- **What people found without being told was "I talk, it tracks".**
- User C got a plan from a short intake chat and never trained it.
- Not checked: whether any workout was changed mid-session according to the workout records (only what people
  typed was read).

## What we worked out

1. **Listen first, then tell.** Athletes are protective of their training. Nobody serious hands their program to a
   stranger. Thom made Wilo listen through an import of his history; user B made it listen by dictating. Wilo
   earns the right to tell you what to do by showing it heard you. User C is the other side: told before being
   listened to, and the plan wasn't theirs.
2. **Wilo never says what it can do next.** User B logged three workouts and was never offered "I've got enough
   now, want me to plan tomorrow from this?" The capability exists; the user didn't know. The fix is the coach
   offering the next step after a logged workout, so nobody needs Thom in the room to explain it.
3. **Wilo is for people who already train.** Not for getting people to train. "Listen first" filters by itself:
   to make Wilo listen, you need training to tell it about.
4. **Wilo doesn't chase.** No guilt, no nagging, no streaks. "Do or do not, there is no try." You can't want it
   for them.
   - First time someone says "I'll try": take them at their word and make the next step tiny ("message me when
     you're at the gym").
   - When there's a real pattern: state the record without judgment ("three Tuesdays planned, none done. Change
     the plan, or leave it?") and hand the choice back.
5. **The tell is in how people talk.** Doers say what they did. Triers say what they're going to do. If Wilo's
   opening question is about what someone is already doing, the answer sorts them in one message.

## What the interview added

Thom talked with user B by phone. This is one person who was asked to try Wilo, so it is a lead, not proof.
Reported by pattern; nothing here is a quote.

- **Why they stopped: life, not the product.** They travelled and didn't train. They said they would backfill and
  start again. Whether they do is the real answer, so watch the log, not the promise.
- **What they came for: a log.** Not a plan, not a coach.
- **What impressed them most:** talking in ordinary gym language and having it logged with almost no corrections.
  Second, that Wilo knows training.
- **What annoyed them:** no bigger view, and no way to flip back to earlier days. Review mode has since covered this.
- **What they expected and never saw:** asking "what did I do last time?", and suggestions. Both exist. They were
  never told. This confirms point 2 above.
- **When they would let Wilo plan:** after four to six weeks of their own data. This confirms point 1, and puts a
  number on "listen first".
- **What would keep them logging daily:** knowing the payoff. Nobody told them what logging earns.
- **Money:** they have paid under $5, one time, for apps. They have also paid a trainer.

### What it means for the landing page (#161, #162)

- **The entry is "talk and it tracks".** It's what impressed the one stranger-like user we have, and it pays off in
  the first minute. The page's first beat shows a thumb ticking every set, which is the part they didn't mention.
- **The second beat shows the mid-workout swap, which none of the three users has used.** It may still be the
  best demo. But today it's Thom's reason for building Wilo, not yet a reason anyone else has given for using it.
- **The page should say the payoff out loud:** log for a few weeks, then Wilo starts suggesting and can plan from
  what you actually do. That is the trade the user said would keep them logging.
- **"What did I do last time?" is a beat worth showing.** It's small, everyone who trains wants it, and Wilo
  already does it.
- **Don't lead with "Wilo plans your training".** This user wants four to six weeks of listening first.
- **Price against the trainer, not the app.** As an app Wilo is worth under $5 to this user. As something that
  does part of what a trainer does, the comparison is different.
- **#166:** a 7 to 14 day trial ends before the four-to-six-week payoff arrives.

## What this changes

- **#165 (Talk to Wilo):** the first conversation with a stranger opens by listening to their training, not
  "answer five questions and here's your plan".
- **Landing page (#161, #162):** the page sells "the plan that bends" to someone with a tracker and a history.
  "Tell Wilo what you're doing and it listens" is a simpler entry that pays off in the first minute of the first
  workout. A candidate variant for the split test.
- **#166 (cost):** Wilo spends almost nothing on people who aren't training. No long pep talks.

## Open questions

- **What is Thom's first question to a stranger who wants help with their training?** He has had this
  conversation a thousand times; it is the visitor section of `coach.md`.
- What's the fastest way for a stranger on their couch, with no export file and not in the gym, to make Wilo
  listen?
- Where does "pay" go in the pipeline, and what has the person felt by then?
- Does a lifter who writes their own programming want Wilo to plan for them, or "set up tomorrow the way I did
  today"? User B's answer: plan for me, but only after four to six weeks of my data.
- Does user B come back and log, now that they know what logging earns?
- Is "talk and it tracks" what strangers want too, or only this user? That is what the split test in #162 is for.

## Parked

- An investor pitch. The one-sentence description is ready; the proof is one stranger through the whole pipeline.
