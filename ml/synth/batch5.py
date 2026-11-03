from lib import *
from base import *

S, SD = S2, S2_DOC
L, LD = L2, L2_DOC
C, CD = C2, C2_DOC
M, MD = ARMS, ARMS_DOC
B, BD = BACK, BACK_DOC
R, RD = LOWER, LOWER_DOC
GW = lambda d: {'collection': 'assigned', 'doc_id': d}
UW = lambda d, w, write: {'collection': 'assigned', 'doc_id': d, 'workout': w, 'write': write}
TODOS = 'Open: 1. Pay rent (Nov 15) [id Pz3mW8tRy5] 2. Email landlord [id d7Ks0QvBn4] 3. Buy creatine [id Xa9Le2HcJ6]'

L_noLunge = edit(L, rep('B-stance lunge', ex('Leg extension', '3x12@70')))

items = [
    # --- update_workout ---
    item(201, '2026-11-10', [
        U('swap b stance for leg extension'),
        A('Done. Leg extension 3x12 @ 70 instead of B-stance lunges. Tap **Load**.', 'update_workout'),
    ], 'And drop the hack squat to 70, my quad is a bit off', 'update_workout',
         UW(LD, edit(L_noLunge, resets('Hack squat', '3x8@70')), False), sc(L, LD)),
    item(202, '2026-11-10', [
        U('And drop the hack squat to 70, my quad is a bit off'),
        A('Hack squat down to 70 for all 3 sets. Ok?', 'update_workout'),
    ], 'Ya', 'update_workout', UW(LD, edit(L_noLunge, resets('Hack squat', '3x8@70')), True), sc(L, LD)),
    item(203, '2026-11-13', [
        U('Uh, what\'s the workout?'),
        A(f'Arms pump: {summary(M)}', 'recent_assigned'),
    ], 'Um, can you do the triceps first and then the biceps? So like pushdowns, overhead, dips, then the curls.', 'update_workout',
         UW(MD, edit(M, chain(mv('Tricep pushdown', 'Treadmill'), mv('Overhead cable', 'Tricep pushdown'), mv('Dip machine', 'Overhead cable'))), False), sc(M, MD)),
    item(204, '2026-11-09', [
        U('read it to me'),
        A(f'Shoulders + biceps + rehab: {summary(S)}', 'get_workout'),
    ], 'take out scap pull ups my elbow is weird', 'update_workout', UW(SD, edit(S, rm('Scapular')), False), sc(S, SD)),
    item(205, '2026-11-12', [
        U('Ya don’t ask just do it if it’s clear.'),
        A('Got it.', 'update_workout'),
        U('what’s left'),
        A(f'Left: {summary(C)}', 'recent_completed', 'get_workout'),
    ], 'make the cable curls 3x12 instead of 15', 'update_workout',
         UW(CD, edit(C, resets('Free motion', '3x12@17')), True), sc(C, CD)),
    item(206, '2026-11-07', [
        U('show me the workout'),
        A(f'Lower-body rehab: {summary(R)}', 'get_workout'),
    ], 'swap step ups for box squats same sets', 'update_workout',
         UW(RD, edit(R, rep('Step up', ex('Box squat', '3x10'))), False), sc(R, RD)),
    item(207, '2026-11-06', [
        U('hey whats on'),
        A(f'Back + hamstrings + triceps: {summary(B)}', 'recent_assigned'),
        U('the meadows row station is taken'),
        A('Want to swap it for a one arm dumbbell row, or do it later?'),
    ], 'Do it later, move it after the cable rows', 'update_workout',
         UW(BD, edit(B, mv('Meadows', 'Double cable row')), False), sc(B, BD)),
    item(208, '2026-11-06', [
        U('the meadows row station is taken'),
        A('Want to swap it for a one arm dumbbell row, or do it later?'),
        U('one arm row'),
        A('Swapping Meadows row for one arm row 3x10 @ 50 each side. Ok?', 'update_workout'),
    ], 'Yes', 'update_workout', UW(BD, edit(B, rep('Meadows', ex('One arm row', '3x10@50 RL'))), True), sc(B, BD)),
    item(209, '2026-11-13', [
        U('read it'),
        A(f'Arms pump: {summary(M)}', 'get_workout'),
    ], 'add 2 sets of dead hang at the start', 'update_workout',
         UW(MD, edit(M, ins('', ex('Dead hang', '2x45t', '~45s each. Opens the shoulder.'))), False), sc(M, MD)),
    item(210, '2026-11-09', [
        U('read it to me'),
        A(f'Shoulders + biceps + rehab: {summary(S)}', 'get_workout'),
        U('Uh, can I do the curls with the EZ bar?'),
        A('Sure. Swap barbell curl for EZ bar curl, same 3x10 @ 45?'),
    ], 'Ya', 'update_workout', UW(SD, edit(S, rep('Barbell curl', ex('EZ bar curl', '3x10@45'))), True), sc(S, SD)),

    # --- get_workout ---
    item(211, '2026-11-13', [], 'swap overhead extension for skull crushers', 'get_workout', GW(MD), sc(M, MD)),
    item(212, '2026-11-10', [
        U('yo'),
        A('Hey Thom! Legs + triceps is loaded. How\'s the quad?'),
    ], 'Quad is meh. Lighten up the leg press', 'get_workout', GW(LD), sc(L, LD)),
    item(213, '2026-11-12', [], 'Uh, can you, um, put the pec deck first? The bench is taken.', 'get_workout', GW(CD), sc(C, CD)),

    # --- no tool ---
    item(214, '2026-11-13', [], 'wow that pump is crazy', None, None, sc(M, MD)),
    item(215, '2026-11-10', [
        U('And drop the hack squat to 70'),
        A('Done. Hack squat is 70 now. Tap **Load**.', 'update_workout'),
    ], 'Perfect thank you', None, None, sc(L, LD)),
    item(216, '2026-11-12', [], 'what’s a good tempo for pec deck', None, None, sc(C, CD)),
    item(217, '2026-11-09', [], 'Wait, sorry, that was my buddy talking, ignore that.', None, None, sc(S, SD)),
    item(218, '2026-11-08', [], 'Whats your name', None, None, None),
    item(219, '2026-11-07', [
        U('swap step ups for box squats same sets'),
        A('Swapping step up for box squat 3x10. Ok?', 'update_workout'),
    ], 'Hold on what\'s a box squat exactly', None, None, sc(R, RD)),
    item(220, '2026-11-06', [], 'Should I eat before or after the gym', None, None, sc(B, BD)),
    item(221, '2026-11-13', [
        U('read it'),
        A(f'Arms pump: {summary(M)}', 'get_workout'),
    ], 'Cool', None, None, sc(M, MD)),
    item(222, '2026-11-09', [], 'Can you talk slower', None, None, sc(S, SD)),
    item(223, '2026-11-11', [], 'I\'m feeling kind of lazy today, give me a pep talk', None, None, sc(CARDIO, CARDIO_DOC)),

    # --- assign_workout ---
    item(224, '2026-11-09', [
        U('plan tomorrow, legs'),
        A(f'Tuesday legs + triceps: {summary(L)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'no lunges, my knee', 'assign_workout', {'workout': L_noLunge, 'write': False}, None),
    item(225, '2026-11-09', [
        U('no lunges, my knee'),
        A(f'Updated: {summary(L_noLunge)}. Save?', 'assign_workout'),
    ], 'ya save', 'assign_workout', {'workout': L_noLunge, 'write': True}, None),
    item(226, '2026-11-11', [
        U('Plan thursday chest'),
        A(f'Thursday chest + biceps: {summary(C)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'Perfect', 'assign_workout', {'workout': C, 'write': True}, None),
    item(227, '2026-11-11', [
        U('Plan thursday chest'),
        A(f'Thursday chest + biceps: {summary(C)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'Uh, add incline dumbbell press after the hammer press, like 3 sets of 10 at 40.', 'assign_workout',
         {'workout': edit(C, ins('Hammer machine press', ex('Incline dumbbell press', '3x10@40'))), 'write': False}, None),
    item(228, '2026-11-12', [
        U('Plan saturday, cardio again'),
        A('25 min treadmill, same as Wednesday?', 'get_profile', 'recent_assigned'),
    ], 'make it 30', 'assign_workout',
         {'workout': workout('Cardio', '2026-11-14', [ex('Treadmill', 't1800', '30 min.')]), 'write': False}, None),
    item(229, '2026-11-12', [
        U('make it 30'),
        A('Saturday cardio: Treadmill 30 min. Save?', 'assign_workout'),
    ], 'Yep', 'assign_workout',
         {'workout': workout('Cardio', '2026-11-14', [ex('Treadmill', 't1800', '30 min.')]), 'write': True}, None),

    # --- reads ---
    item(230, '2026-11-11', [], 'how was monday and tuesday', 'recent_completed', {'limit': 3}, None),
    item(231, '2026-11-10', [], 'what have I logged so far today', 'recent_completed', {'limit': 1}, sc(L, LD)),
    item(232, '2026-11-14', [
        U('Can you plan next week'),
        A('Sure. Want me to look at how this week went first?'),
    ], 'Ya', 'recent_completed', {'limit': 7}, None),
    item(233, '2026-11-13', [], 'Uh, did I finish all the sets on Thursday?', 'recent_completed', {'limit': 2}, None),
    item(234, '2026-11-09', [], 'What’s planned for this week', 'recent_assigned', {'limit': 7}, sc(S, SD)),
    item(235, '2026-11-11', [
        U('Hey'),
        A('Hey Thom! Cardio today.'),
    ], 'Can you change thursdays workout to add more triceps', 'recent_assigned', {'limit': 5}, sc(CARDIO, CARDIO_DOC)),
    item(236, '2026-11-13', [], 'what did I do for hammer curls before', 'exercise_history', {'name': 'Hammer curl', 'limit': 3}, sc(M, MD)),
    item(237, '2026-11-10', [], 'How much did I leg press last week', 'exercise_history', {'name': 'Leg press', 'limit': 2}, sc(L, LD)),
    item(238, '2026-11-12', [
        U('Can we add flys'),
        A('Sure. Cable or pec deck?'),
    ], 'Cable, same weight as last time', 'exercise_history', {'name': 'Cable fly', 'limit': 2}, sc(C, CD)),
    item(239, '2026-11-08', [], 'Show me all the exercise names, I want to clean up duplicates', 'exercise_names', {}, None),
    item(240, '2026-11-13', [], 'Have I done anything like tricep kickbacks before? not sure what I called it', 'exercise_names', {}, sc(M, MD)),

    # --- profile ---
    item(241, '2026-11-09', [], 'I tweaked my lower back yesterday picking up a box, keep that in mind', 'get_profile', {}, sc(S, SD)),
    item(242, '2026-11-09', [
        U('I tweaked my lower back yesterday picking up a box, keep that in mind'),
        A('Sorry to hear. Add "lower back tweak, avoid heavy hinges" to limitations?', 'get_profile'),
    ], 'Yes', 'update_profile', {
        'limitations': '- 2026-10-24: Torn quadriceps. Isometrics and walking help.\n- 2026-10-24: Right hamstring twinges on heavy hinges.\n- 2026-11-09: Tweaked lower back lifting a box. Avoid heavy hinges for now.',
        'write': False}, sc(S, SD)),
    item(243, '2026-11-09', [
        U('Yes'),
        A('Here\'s the change, limitations + "2026-11-09: Tweaked lower back lifting a box. Avoid heavy hinges for now." Save?', 'update_profile'),
    ], 'Save it', 'update_profile', {
        'limitations': '- 2026-10-24: Torn quadriceps. Isometrics and walking help.\n- 2026-10-24: Right hamstring twinges on heavy hinges.\n- 2026-11-09: Tweaked lower back lifting a box. Avoid heavy hinges for now.',
        'write': True}, sc(S, SD)),
    item(244, '2026-11-12', [
        U('Note for you: I prefer short workouts on thursdays, I have work after'),
        A('Got it. Add "Thursday workouts under 45 min" to your plan?', 'get_profile'),
    ], 'yes', 'update_profile', {
        'plan': '- 2026-10-24: Goal: strength.\n- 2026-10-25: Weekly split: Mon shoulders + biceps + rehab, Tue legs + triceps, Wed cardio, Thu chest + biceps, Fri back + hamstrings + triceps, Sat cardio, Sun rest.\n- 2026-11-12: Keep Thursday workouts under 45 min (work after).',
        'write': False}, sc(C, CD)),
    item(245, '2026-11-02', [], 'What injuries do you have on file for me', 'get_profile', {}, None),
    item(246, '2026-11-08', [], 'Wilo, what\'s the right way to progress my lifts? What\'s your approach?', 'coaching_method', {}, None),

    # --- todos ---
    item(247, '2026-11-12', [], 'Add pay rent for the 15th', 'add_todo', {'text': 'Pay rent', 'due': '2026-11-15'}, None),
    item(248, '2026-11-12', [], 'Uh, add a to-do to email my landlord about the heater.', 'add_todo', {'text': 'Email landlord about the heater'}, None),
    item(249, '2026-11-12', [], 'what’s still open', 'list_todos', {}, None),
    item(250, '2026-11-12', [U('what’s still open'), A(TODOS, 'list_todos')],
         'bought creatine', 'update_todo', {'doc_id': 'Xa9Le2HcJ6', 'done': True}, None),
]

write(items, 201)
