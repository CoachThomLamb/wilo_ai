"""Round 2 (2026-10-29), aimed at wilo-ft's weak spots on ml/test.jsonl:
- a short yes after a dry run ("...Save it?" / "Ok?") → the same tool again with write=True (it kept write=False);
- adding an exercise without a weight → exercise_history first (the real chats look it up before adding);
- fillers and thinking out loud after Wilo flags something → no tool.
"""
from lib import *
from base import *

S, SD = SHOULDERS, SHOULDERS_DOC
L, LD = LEGS, LEGS_DOC
C, CD = CHEST, CHEST_DOC
B, BD = BACK, BACK_DOC
R, RD = LOWER, LOWER_DOC
P, PD = PUMP, PUMP_DOC
M, MD = ARMS, ARMS_DOC
UW = lambda d, w, write: {'collection': 'assigned', 'doc_id': d, 'workout': w, 'write': write}
EH = lambda name, limit=2: {'name': name, 'limit': limit}

items = [
    # --- yes after a dry run of update_workout → write=True ---
    item(301, '2026-11-06', [
        U('meadows row is taken'),
        A("I'll swap the Meadows row for a single arm dumbbell row, 3x10 @ 60. Ok?", 'update_workout'),
    ], 'Ys', 'update_workout',
         UW(BD, edit(B, rep('Meadows row', ex('Single arm dumbbell row', '3x10@60'))), True), sc(B, BD)),
    item(302, '2026-11-02', [
        U('can we add a 5 min treadmill at the end too'),
        A('I\'ll add a 5 minute easy treadmill walk at the end of today\'s shoulders workout. Save it?', 'update_workout'),
    ], 'Ya', 'update_workout', UW(SD, edit(S, ins(None, TREAD5())), True), sc(S, SD)),
    item(303, '2026-11-05', [
        U('put the curls before the pec deck'),
        A('Barbell curl now comes right before the pec deck. Ok?'),
    ], 'yep', 'update_workout', UW(CD, edit(C, mv('Barbell curl', 'Hammer machine press')), True), sc(C, CD)),
    item(304, '2026-11-03', [
        U('Hack squat 3 sets of 10 at 80 instead'),
        A('Hack squat goes to 3x10 @ 80 (was 3x8 @ 90). Save it?', 'update_workout'),
    ], 'Yes', 'update_workout', UW(LD, edit(L, resets('Hack squat', '3x10@80')), True), sc(L, LD)),
    item(305, '2026-11-07', [
        U('Can you add a massage before the dragging, 10 minutes'),
        A("I'll add a 10 minute massage at the start, before the dragging. Same as last time. Save it?", 'update_workout'),
    ], 'ya do it', 'update_workout', UW(RD, edit(R, ins('', ex('Massage', 't600'))), True), sc(R, RD)),
    item(306, '2026-11-09', [
        U('drop the pushups at the end'),
        A('Pushups are out. Everything else stays. Ok?', 'update_workout'),
    ], 'k', 'update_workout', UW(PD, edit(P, rm('Pushups')), True), sc(P, PD)),
    item(307, '2026-11-13', [
        U('Swap preacher curls for spider curls, same weight'),
        A('Spider curl 3x12 @ 30 in place of the preacher curl. Save it?'),
    ], 'Sure', 'update_workout',
         UW(MD, edit(M, rep('Preacher curl', ex('Spider curl', '3x12@30'))), True), sc(M, MD)),
    item(308, '2026-11-06', [
        U('Hey can you add three sets of face pulls before the pulldown'),
        A('Last face pulls were 3x12 @ 25. I\'ll put 3x12 @ 25 right before the pulldown. Ok?', 'exercise_history'),
    ], 'Ya', 'update_workout',
         UW(BD, edit(B, ins('Meadows row', ex('Face pull', '3x12@25'))), True), sc(B, BD)),
    item(309, '2026-11-02', [
        U('Lateral raises at 10 not 5'),
        A('Lateral raise goes to 3x12 @ 10. Save?', 'update_workout'),
    ], 'Perfect', 'update_workout', UW(SD, edit(S, resets('Lateral raise', '3x12@10')), True), sc(S, SD)),
    item(310, '2026-11-05', [
        U('my shoulder is not happy, take out the hammer press'),
        A('Hammer machine press is out for today. Pec deck stays, stop if it pinches. Save it?', 'update_workout'),
    ], 'Ya don’t ask just do it if it’s clear.', 'update_workout',
         UW(CD, edit(C, rm('Hammer machine press')), True), sc(C, CD)),
    item(311, '2026-11-10', [
        U('Can we do leg press 4 sets'),
        A('Leg press goes to 4x10 @ 200. Ok?', 'get_workout', 'update_workout'),
    ], 'yes please', 'update_workout', UW(L2_DOC, edit(L2, resets('Leg press', '4x10@200')), True), sc(L2, L2_DOC)),
    item(312, '2026-11-12', [
        U('add dips at the end, the machine, like last time'),
        A('Dip machine 3x12 @ 140 at the end, same as last time. Save it?', 'exercise_history', 'update_workout'),
    ], 'Yup go', 'update_workout',
         UW(C2_DOC, edit(C2, ins(None, ex('Dip machine', '3x12@140'))), True), sc(C2, C2_DOC)),
    item(313, '2026-11-07', [
        U('step ups are bugging my knee, swap for leg extension iso holds'),
        A("I'll swap step ups for leg extension holds, 3x30s. Ok?"),
    ], 'Ok go', 'update_workout',
         UW(RD, edit(R, rep('Step up', ex('Leg extension hold', '3x30t'))), True), sc(R, RD)),
    item(314, '2026-11-09', [
        U('I want the cable fly first'),
        A('Cable fly moves to right after the dead hang. Save it?', 'update_workout'),
    ], 'Yeah', 'update_workout', UW(PD, edit(P, mv('Cable fly', 'Dead hang')), True), sc(P, PD)),

    # --- not a plain yes: a new change on top of the dry run → still a dry run ---
    item(315, '2026-11-06', [
        U('meadows row is taken'),
        A("I'll swap the Meadows row for a single arm dumbbell row, 3x10 @ 60. Ok?", 'update_workout'),
    ], 'ya but make it 70', 'update_workout',
         UW(BD, edit(B, rep('Meadows row', ex('Single arm dumbbell row', '3x10@70'))), False), sc(B, BD)),
    item(316, '2026-11-03', [
        U('Hack squat 3 sets of 10 at 80 instead'),
        A('Hack squat goes to 3x10 @ 80 (was 3x8 @ 90). Save it?', 'update_workout'),
    ], 'Yes and drop the lunges', 'update_workout',
         UW(LD, edit(L, chain(resets('Hack squat', '3x10@80'), rm('B-stance'))), False), sc(L, LD)),
    item(317, '2026-11-13', [
        U('Swap preacher curls for spider curls, same weight'),
        A('Spider curl 3x12 @ 30 in place of the preacher curl. Save it?', 'update_workout'),
    ], 'no actually keep the preacher', None, None, sc(M, MD)),
    item(318, '2026-11-02', [
        U('can we add a 5 min treadmill at the end too'),
        A("I'll add a 5 minute easy treadmill walk at the end of today's shoulders workout. Save it?", 'update_workout'),
    ], 'wait hold on', None, None, sc(S, SD)),

    # --- adding an exercise with no weight given → look it up first ---
    item(319, '2026-11-02', [], 'can you add face pulls at the end', 'exercise_history', EH('Face pull'), sc(S, SD)),
    item(320, '2026-11-06', [
        U('read me the workout'),
        A(f'Back + hamstrings + triceps: {summary(B)}', 'get_workout'),
    ], 'Hey could we add some hammer curls after the cable row', 'exercise_history', EH('Hammer curl'), sc(B, BD)),
    item(321, '2026-11-03', [], 'add calf raises after the leg press', 'exercise_history', EH('Calf raise'), sc(L, LD)),
    item(322, '2026-11-05', [
        U('what’s today'),
        A(f'Chest + biceps: {summary(C)}', 'recent_assigned'),
    ], 'can we throw in some incline dumbbell press after the hammer press', 'exercise_history',
         EH('Incline dumbbell press'), sc(C, CD)),
    item(323, '2026-11-09', [], 'Uh, add, uh, overhead cable extensions at the end please', 'exercise_history',
         EH('Overhead cable extension'), sc(P, PD)),
    item(324, '2026-11-07', [], 'Can you add a couple sets of hip thrusts in there', 'exercise_history',
         EH('Hip thrust'), sc(R, RD)),
    item(325, '2026-11-13', [], 'Add some reverse curls before the pushdowns', 'exercise_history',
         EH('Reverse curl'), sc(M, MD)),
    item(326, '2026-11-12', [
        U('ok'),
        A('Go get it. Tap **Load** if anything changes.'),
    ], 'actually I want to do some dumbbell flys too', 'exercise_history', EH('Dumbbell fly'), sc(C2, C2_DOC)),
    item(327, '2026-11-06', [], 'swap the dip machine for skull crushers', 'exercise_history',
         EH('Skull crusher'), sc(B, BD)),
    item(328, '2026-11-10', [], 'Hey can we add some goblet squats at the start', 'exercise_history',
         EH('Goblet squat'), sc(L2, L2_DOC)),
    # ...but with sets and weight given, change it straight away
    item(329, '2026-11-02', [], 'add face pulls at the end 3x12 at 25', 'update_workout',
         UW(SD, edit(S, ins(None, ex('Face pull', '3x12@25'))), False), sc(S, SD)),
    item(330, '2026-11-03', [], 'add calf raises after leg press, 3 sets of 15 at 90', 'update_workout',
         UW(LD, edit(L, ins('Leg press', ex('Calf raise', '3x15@90'))), False), sc(L, LD)),
    item(331, '2026-11-13', [], 'swap the dip machine for skull crushers 3x10 at 50', 'update_workout',
         UW(MD, edit(M, rep('Dip machine', ex('Skull crusher', '3x10@50'))), False), sc(M, MD)),
    # ...and planning a different split: check what they did on the exercises it would use
    item(332, '2026-11-05', [
        U('can we change today'),
        A('Sure. What do you want instead of chest + biceps?'),
    ], 'i did biceps yesterday so maybe pull and then triceps instead', 'exercise_history',
         EH('Hammer machine pulldown'), sc(C, CD)),
    item(333, '2026-11-09', [
        U('change of plans'),
        A('Ok, what are you thinking?'),
    ], 'legs today instead of push, my chest is still sore', 'exercise_history', EH('Leg press'), sc(P, PD)),

    # --- fillers / thinking out loud → no tool ---
    item(334, '2026-11-07', [
        U('can we put RDLs in today'),
        A("Before I add them: today is lower-body rehab and most cues say stop if the right hamstring twinges. "
          "RDLs load the hamstring hard. Want to try them light, or leave them for next week?",
          'recent_assigned', 'exercise_history'),
    ], 'Mm-hmm.', None, None, sc(R, RD)),
    item(335, '2026-11-06', [
        U('why is the RDL so light'),
        A('Last time the hamstring twinged at 60, so I set 50 to rebuild.', 'exercise_history'),
    ], 'right', None, None, sc(B, BD)),
    item(336, '2026-11-02', [
        U('should I do the press'),
        A('If it pinches at the top, drop to 10 lbs or skip it today. Dead hangs first help.'),
    ], 'hmm ok let me see how it feels', None, None, sc(S, SD)),
    item(337, '2026-11-03', [
        U('how much rest on hack squat'),
        A('About 2 minutes between sets.'),
    ], 'gotcha', None, None, sc(L, LD)),
    item(338, '2026-11-05', [
        U('pec deck or cable fly today'),
        A('Pec deck is planned. Cable fly works the same if the deck is busy.'),
    ], 'Uh, I think, uh, let me go look if it’s free', None, None, sc(C, CD)),
    item(339, '2026-11-09', [], 'ok starting now', None, None, sc(P, PD)),
    item(340, '2026-11-13', [
        U('is 50 too heavy for curls'),
        A('Last time all 3x10 at 45 were clean, so 50 is a small step. Try it and drop if form goes.'),
    ], 'Yeah, I know, I heard you, you don’t need to say all of it out loud.', None, None, sc(M, MD)),
    item(341, '2026-11-06', [
        U('can I add deadlifts today'),
        A("Today has RDLs and leg curls, and the right hamstring has been twinging. I'd skip heavy deadlifts. Ok?"),
    ], 'Yeah fair', None, None, sc(B, BD)),
    item(342, '2026-11-10', [], 'one sec, someone’s talking to me', None, None, sc(L2, L2_DOC)),
    item(343, '2026-11-12', [
        U('what weight on the pec deck'),
        A('100 for 3x12, same as last week.'),
    ], 'Mhm', None, None, sc(C2, C2_DOC)),
    item(344, '2026-11-07', [], 'Okay, I’m at the sled now.', None, None, sc(R, RD)),
    item(345, '2026-11-02', [
        U('Hey'),
        A("Hey Thom. Today is shoulders + biceps + rehab, it's loaded. Anything hurting?", 'recent_assigned'),
    ], 'Nope all good', None, None, sc(S, SD)),
    item(346, '2026-11-09', [
        U('hammer press is busy'),
        A('Do the incline dumbbell press first and come back to it. Want me to move it?'),
    ], 'Hmm, I’ll just wait a minute', None, None, sc(P, PD)),
    item(347, '2026-11-03', [], 'That was a hard set', None, None, sc(L, LD)),
    item(348, '2026-11-13', [
        U('done with curls'),
        A('Nice. Pushdowns next, 3x12 @ 45.'),
    ], 'Cool', None, None, sc(M, MD)),
    item(349, '2026-11-05', [], 'Uh, so, I don’t know, maybe, um, never mind.', None, None, sc(C, CD)),
    item(350, '2026-11-06', [
        U('Can you add sword raises before the meadows rows'),
        A('Last time you did sword raises 3x6 each side at 5. Same before the Meadows row?', 'exercise_history'),
    ], 'Uh, hold on, I’ll do them after actually, um, let me think', None, None, sc(B, BD)),
]

if __name__ == '__main__':
    write(items, 301)
