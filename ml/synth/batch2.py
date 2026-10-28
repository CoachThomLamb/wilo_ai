from lib import *
from base import *

S, SD = SHOULDERS, SHOULDERS_DOC
L, LD = LEGS, LEGS_DOC
C, CD = CHEST, CHEST_DOC
B, BD = BACK, BACK_DOC
R, RD = LOWER, LOWER_DOC
P, PD = PUMP, PUMP_DOC
GW = lambda d: {'collection': 'assigned', 'doc_id': d}
UW = lambda d, w, write: {'collection': 'assigned', 'doc_id': d, 'workout': w, 'write': write}

items = [
    # --- mid-workout, workout already read in this chat → update_workout ---
    item(51, '2026-11-07', [
        U('Uh, what\'s on for today?'),
        A(f'Lower-body rehab: {summary(R)}', 'recent_assigned'),
    ], 'Okay, um, the sled, uh, somebody\'s using the turf. So can we just put the dragging at the end instead?',
         'update_workout', UW(RD, edit(R, mv('Dragging', 'Bulgarian')), False), sc(R, RD)),

    item(52, '2026-11-07', [
        U('Okay, um, the sled, uh, somebody\'s using the turf. So can we just put the dragging at the end instead?'),
        A('Moving dragging to after the Bulgarian holds, before the walk. Ok?', 'update_workout'),
    ], 'Yeah yeah do it', 'update_workout', UW(RD, edit(R, mv('Dragging', 'Bulgarian')), True), sc(R, RD)),

    item(53, '2026-11-09', [
        U('read it'),
        A(f'Push pump: {summary(P)}', 'get_workout'),
        U('Ok'),
        A('Have fun.'),
    ], 'incline db press the 40s are gone only 35s', 'update_workout',
         UW(PD, edit(P, resets('Incline dumbbell press', '3x10@35')), False), sc(P, PD)),

    item(54, '2026-11-09', [
        U('Ya don’t ask just do it if it’s clear.'),
        A('Got it.'),
        U('What’s left'),
        A(f'Left: {summary(P)}', 'recent_completed', 'get_workout'),
    ], 'Add 2 more sets of pushups', 'update_workout',
         UW(PD, edit(P, resets('Pushups', '4x15')), True), sc(P, PD)),

    item(55, '2026-11-06', [
        U('whats today'),
        A(f'Back + hamstrings + triceps: {summary(B)}', 'recent_assigned'),
        U('Can you put the treadmill at the end instead and make it 15'),
        A('Moving the treadmill to the end as 15 min. Ok?', 'update_workout'),
    ], 'Perfect', 'update_workout', UW(BD, edit(B, chain(rm('Treadmill'), ins(None, ex('Treadmill', 't900', '15 min easy walk.')))), True), sc(B, BD)),

    item(56, '2026-11-05', [
        U('show me the workout'),
        A(f'Chest + biceps: {summary(C)}', 'get_workout'),
        U('decline front raise is killing me'),
        A('Want to drop to 3 sets of 4, or take it out today?'),
    ], '3 of 4', 'update_workout', UW(CD, edit(C, resets('Decline front raise', '3x4@5')), False), sc(C, CD)),

    item(57, '2026-11-02', [
        U('Load it up'),
        A(f'Today is shoulders + biceps + rehab: {summary(S)}', 'get_workout'),
        U('skip the massage today no time'),
        A('Massage is out. Tap **Load**.', 'update_workout'),
    ], 'also switch barbell curl for cable curl, bar is taken', 'update_workout',
         UW(SD, edit(S, chain(rm('Massage'), rep('Barbell curl', ex('Cable curl', '3x10@30')))), False), sc(S, SD)),

    item(58, '2026-11-03', [
        U('whats my workout'),
        A(f'Legs + triceps: {summary(L)}', 'recent_assigned'),
        U('Tricep pushdown after skull crushers'),
        A('Moving tricep pushdown after the skull crusher pushups. Ok?', 'update_workout'),
    ], 'k', 'update_workout', UW(LD, edit(L, mv('Tricep pushdown', 'Skull crusher')), True), sc(L, LD)),

    item(59, '2026-11-07', [
        U('Uh, what\'s on for today?'),
        A(f'Lower-body rehab: {summary(R)}', 'recent_assigned'),
        U('Okay.'),
        A('How\'s the hamstring?'),
    ], 'Hamstring is kinda twingy, so let\'s, uh, take out the leg curls and just do more step ups, like 4 sets.', 'update_workout',
         UW(RD, edit(R, chain(rm('Single leg curls'), resets('Step up', '4x10'))), False), sc(R, RD)),

    item(60, '2026-11-09', [
        U('read it'),
        A(f'Push pump: {summary(P)}', 'get_workout'),
    ], 'Cable fly is busy. Pec deck instead 3x12 at 100', 'update_workout',
         UW(PD, edit(P, rep('Cable fly', ex('Pec deck', '3x12@100'))), False), sc(P, PD)),

    item(61, '2026-11-06', [
        U('hamstring is tight today. Take out the RDLs and the leg curls just do upper'),
        A('Taking out the RDLs and double leg curls, rest stays. Ok?', 'update_workout'),
    ], 'Yes', 'update_workout', UW(BD, edit(B, chain(rm('Dumbbell RDL'), rm('Double leg curls'))), True), sc(B, BD)),

    item(62, '2026-11-05', [
        U('Hey Wilo whats on'),
        A(f'Chest + biceps: {summary(C)}', 'recent_assigned'),
    ], 'Can you add a uh, a set of dead hangs at the very end too like a cool down', 'update_workout',
         UW(CD, edit(C, ins(None, ex('Dead hang', '1x45t', 'Cool down.'))), False), sc(C, CD)),

    item(63, '2026-11-03', [
        U('whats today'),
        A(f'Legs + triceps: {summary(L)}', 'get_workout'),
        U('leg press is free yet?'),
        A("I can't see the gym, but you could start with crane-plane and come back to it."),
    ], 'ya do that, crane plane first then leg press', 'update_workout',
         UW(LD, edit(L, mv('Crane-plane', 'Treadmill')), False), sc(L, LD)),

    # --- first mention, not read yet → get_workout ---
    item(64, '2026-11-07', [], 'the sled is taken can i do something else', 'get_workout', GW(RD), sc(R, RD)),
    item(65, '2026-11-09', [
        U('hi'),
        A('Hi Thom! Push pump is loaded. Go get it.'),
    ], 'Only 35s for the incline press, change it', 'get_workout', GW(PD), sc(P, PD)),
    item(66, '2026-11-06', [], 'Move the dip machine before the rows', 'get_workout', GW(BD), sc(B, BD)),
    item(67, '2026-11-05', [], 'Uh, can you, um, swap the cable curls for preacher curls?', 'get_workout', GW(CD), sc(C, CD)),
    item(68, '2026-11-02', [], 'whats next after serratus', 'get_workout', GW(SD), sc(S, SD)),

    # --- no tool ---
    item(69, '2026-11-07', [], 'how long should I rest between sets of step ups', None, None, sc(R, RD)),
    item(70, '2026-11-09', [
        U('Cable fly is busy. Pec deck instead 3x12 at 100'),
        A('Done. Pec deck is in. Tap **Load**.', 'update_workout'),
    ], 'Got it', None, None, sc(P, PD)),
    item(71, '2026-10-31', [], 'Hey can you hear me', None, None, None),
    item(72, '2026-11-06', [], 'my hamstring feels weird after the RDLs, is that normal', None, None, sc(B, BD)),
    item(73, '2026-11-03', [
        U('whats today'),
        A(f'Legs + triceps: {summary(L)}', 'get_workout'),
    ], 'Okay, perfect. Let\'s go.', None, None, sc(L, LD)),
    item(74, '2026-11-05', [
        U('decline front raise is killing me'),
        A('Want to drop to 3 sets of 4, or take it out today?'),
    ], 'Hmm let me try one more set first', None, None, sc(C, CD)),
    item(75, '2026-11-02', [], 'You don’t need to read it all to me just keep it short', None, None, sc(S, SD)),
    item(76, '2026-11-01', [], 'whats the difference between RDL and a regular deadlift', None, None, None),
    item(77, '2026-11-07', [
        U('Hamstring is kinda twingy, so let\'s take out the leg curls'),
        A('Leg curls are out. Tap **Load**.', 'update_workout'),
    ], 'Tapped load. Looks good', None, None, sc(R, RD)),
    item(78, '2026-11-04', [], 'I tapped load and nothing changed', None, None, sc(C, CD)),

    # --- plan / assign ---
    item(79, '2026-11-06', [
        U('plan tomorrow lower body rehab'),
        A('Saturday is cardio on your split. Swap it for lower-body rehab?', 'get_profile', 'recent_completed'),
        U('Ya'),
        A(f'Draft for Saturday: {summary(R)}. Save?', 'assign_workout'),
    ], 'Take out the step ups, my knee. Otherwise good', 'assign_workout',
         {'workout': edit(R, rm('Step up')), 'write': False}, None),
    item(80, '2026-11-06', [
        U('Take out the step ups, my knee. Otherwise good'),
        A(f'Updated draft: {summary(edit(R, rm("Step up")))}. Save?', 'assign_workout'),
    ], 'Save it', 'assign_workout', {'workout': edit(R, rm('Step up')), 'write': True}, None),
    item(81, '2026-11-08', [
        U('want a push day tomorrow, just pump, no rehab'),
        A(f'Push pump for Monday: {summary(P)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'Ya post it', 'assign_workout', {'workout': P, 'write': True}, None),
    item(82, '2026-11-08', [
        U('want a push day tomorrow, just pump, no rehab'),
        A(f'Push pump for Monday: {summary(P)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'swap dip machine for close grip bench 3x8 at 95', 'assign_workout',
         {'workout': edit(P, rep('Dip machine', ex('Close grip bench', '3x8@95'))), 'write': False}, None),
    item(83, '2026-11-02', [
        U('Can you do the whole week'),
        A(f'Monday is saved. Tuesday legs + triceps: {summary(L)}. Save?', 'assign_workout', 'assign_workout'),
    ], 'Yup', 'assign_workout', {'workout': L, 'write': True}, None),
    item(84, '2026-11-02', [
        U('Yup'),
        A('Tuesday is saved. Wednesday cardio, 25 min?', 'assign_workout'),
    ], 'Ya', 'assign_workout',
         {'workout': workout('Cardio', '2026-11-04', [ex('Treadmill', 't1500', '25 min.')]), 'write': True}, None),
    item(85, '2026-11-04', [
        U('Can you plan tomorrow'),
        A('Thursday is chest + biceps. Same as last Thursday?', 'get_profile', 'recent_completed'),
    ], 'yep same but bump the curls to 50', 'assign_workout',
         {'workout': edit(C, resets('Barbell curl', '3x10@50')), 'write': False}, None),

    # --- reads ---
    item(86, '2026-11-07', [], 'How’d tuesday go, did I finish everything', 'recent_completed', {'limit': 5}, None),
    item(87, '2026-11-09', [
        U('just finished'),
        A('Nice work. Want a quick review?'),
    ], 'Sure', 'recent_completed', {'limit': 1}, sc(P, PD)),
    item(88, '2026-11-01', [], 'Uh, can you look at my last few workouts and tell me what I\'ve been skipping?', 'recent_completed', {'limit': 10}, None),
    item(89, '2026-11-05', [
        U('Hey'),
        A('Hey Thom! Want me to load today?'),
    ], 'For thursday swap the barbell curls for preacher curls', 'recent_assigned', {'limit': 5}, sc(S, SD)),
    item(90, '2026-11-01', [], 'Is the whole week planned or just monday', 'recent_assigned', {'limit': 7}, None),
    item(91, '2026-11-07', [], 'What did I do for step ups last time', 'exercise_history', {'name': 'Step up', 'limit': 3}, sc(R, RD)),
    item(92, '2026-11-09', [
        U('Can you add close grip bench'),
        A('Sure, where in the workout?'),
    ], 'After the dips, same as last time weight wise', 'exercise_history', {'name': 'Close grip bench', 'limit': 2}, sc(P, PD)),
    item(93, '2026-11-02', [], 'how heavy was my last sword raise', 'exercise_history', {'name': 'Sword raise', 'limit': 2}, sc(S, SD)),
    item(94, '2026-11-01', [], 'Can you list all the exercises I’ve ever done', 'exercise_names', {}, None),
    item(95, '2026-11-01', [
        U('what am i supposed to avoid again with my hamstring'),
    ], 'what does my profile say', 'get_profile', {}, None),
    item(96, '2026-11-07', [
        U('Hamstring is kinda twingy, so let\'s take out the leg curls'),
        A('Leg curls are out. Want me to note the twinge in your profile?', 'update_workout', 'get_profile'),
    ], 'Ya', 'update_profile', {
        'limitations': '- 2026-10-24: Torn quadriceps. Isometrics and walking help.\n- 2026-10-24: Right hamstring twinges on heavy hinges.\n- 2026-11-07: Right hamstring twingy on seated leg curls. Left them out.',
        'write': False}, sc(R, RD)),
    item(97, '2026-11-01', [
        U('i want to train 5 days not 6 from now on, drop saturday cardio'),
        A('Here\'s the plan change: Sat cardio → rest. Save?', 'get_profile', 'update_profile'),
    ], 'Save', 'update_profile', {
        'plan': '- 2026-10-24: Goal: strength.\n- 2026-10-25: Weekly split: Mon shoulders + biceps + rehab, Tue legs + triceps, Wed cardio, Thu chest + biceps, Fri back + hamstrings + triceps, Sun rest.\n- 2026-11-01: Saturday is rest now (5 days a week).',
        'write': True}, None),
    item(98, '2026-10-30', [], 'How are you supposed to coach me, like what’s your process', 'coaching_method', {}, None),
    item(99, '2026-11-01', [
        U('Hey'),
        A('Hey Thom, what\'s up?'),
    ], 'Can you review my week and plan next week', 'coaching_method', {}, None),
    item(100, '2026-11-02', [], 'remind me to buy protein powder', 'add_todo', {'text': 'Buy protein powder'}, None),
]

write(items, 51)
