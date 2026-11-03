from lib import *
from base import *

S, SD = SHOULDERS, SHOULDERS_DOC
C, CD = CHEST, CHEST_DOC
B, BD = BACK, BACK_DOC
P, PD = PUMP, PUMP_DOC
M, MD = ARMS, ARMS_DOC
K, KD = CARDIO, CARDIO_DOC
GW = lambda d: {'collection': 'assigned', 'doc_id': d}
UW = lambda d, w, write: {'collection': 'assigned', 'doc_id': d, 'workout': w, 'write': write}
TODOS = 'Open: 1. Laundry [id Fg5Tn2WqZ8] 2. Meal prep Sunday (Nov 8) [id k0Mb7RxEc3] 3. Return Amazon package [id Vs4Yh9PoL1]'

# A new user's first workout (pushups default, per coach.md).
NEW = workout('first-workout-nov-3', '2026-11-03', [
    ex('Pushups', '3x10'), ex('Bodyweight squat', '3x12'), ex('Plank', '3x30t'), ex('Walk', 't600', '10 min easy.')])
NEW_DOC = doc_id('first', '2026-11-02', '20:44')

items = [
    # --- update_workout ---
    item(251, '2026-11-02', [
        U('read me the rest'),
        A(f'Left: {summary(S)}', 'recent_completed', 'get_workout'),
    ], 'swap sword raises for face pulls 3x12 at 25', 'update_workout',
         UW(SD, edit(S, rep('Sword raise', ex('Face pull', '3x12@25'))), False), sc(S, SD)),
    item(252, '2026-11-05', [
        U('whats today'),
        A(f'Chest + biceps: {summary(C)}', 'recent_assigned'),
        U('hammer press is taken'),
        A('Want to do pec deck first and come back to it?'),
    ], 'Ya', 'update_workout', UW(CD, edit(C, mv('Pec deck', 'Decline front raise')), False), sc(C, CD)),
    item(253, '2026-11-06', [
        U('Ya don’t ask just do it if it’s clear.'),
        A('Got it.'),
        U('read it'),
        A(f'{summary(B)}', 'get_workout'),
    ], 'dip machine 4 sets', 'update_workout', UW(BD, edit(B, resets('Dip machine', '4x12@140')), True), sc(B, BD)),
    item(254, '2026-11-09', [
        U('Uh, read me the workout, quick.'),
        A(f'Push pump: {summary(P)}', 'get_workout'),
    ], 'Uh, so cable fly, I\'m gonna do it at 35 instead of 30, I think 30 is too light now.', 'update_workout',
         UW(PD, edit(P, resets('Cable fly', '3x12@35')), False), sc(P, PD)),
    item(255, '2026-11-09', [
        U('Uh, so cable fly, I\'m gonna do it at 35 instead of 30.'),
        A('Cable fly up to 35 for all 3 sets. Ok?', 'update_workout'),
    ], 'yeah go', 'update_workout', UW(PD, edit(P, resets('Cable fly', '3x12@35')), True), sc(P, PD)),
    item(256, '2026-11-13', [
        U('whats on'),
        A(f'Arms pump: {summary(M)}', 'recent_assigned'),
    ], 'Drop the dip machine, add another round of hammer curls instead', 'update_workout',
         UW(MD, edit(M, chain(rm('Dip machine'), resets('Hammer curl', '4x10@25'))), False), sc(M, MD)),
    item(257, '2026-11-03', [
        U('what do I do today'),
        A(f'Your first workout: {summary(NEW)}', 'recent_assigned'),
    ], 'I cant do 10 pushups lol, can we do like 5', 'update_workout',
         UW(NEW_DOC, edit(NEW, resets('Pushups', '3x5')), False), sc(NEW, NEW_DOC)),
    item(258, '2026-11-03', [
        U('I cant do 10 pushups lol, can we do like 5'),
        A('Pushups down to 3 sets of 5. Ok?', 'update_workout'),
    ], 'yes thanks', 'update_workout', UW(NEW_DOC, edit(NEW, resets('Pushups', '3x5')), True), sc(NEW, NEW_DOC)),
    item(259, '2026-11-11', [
        U('whats today'),
        A('Cardio: Treadmill 25 min.', 'get_workout'),
    ], 'Add 10 min of stretching after', 'update_workout',
         UW(KD, edit(K, ins(None, ex('Stretching', 't600', '10 min.'))), False), sc(K, KD)),
    item(260, '2026-11-05', [
        U('Uh, pull up the workout'),
        A(f'Chest + biceps: {summary(C)}', 'get_workout'),
        U('Take out decline front raise'),
        A('Done. Decline front raise is out. Tap **Load**.', 'update_workout'),
    ], 'and the serratus shrugs too', 'update_workout',
         UW(CD, edit(C, chain(rm('Decline front raise'), rm('Serratus'))), False), sc(C, CD)),

    # --- get_workout ---
    item(261, '2026-11-03', [], 'what is a plank and how long do i hold it', None, None, sc(NEW, NEW_DOC)),
    item(262, '2026-11-13', [], 'Can we move curls to the end', 'get_workout', GW(MD), sc(M, MD)),
    item(263, '2026-11-09', [
        U('hey wilo'),
        A('Hey Thom! Push pump is loaded.'),
    ], 'Uh, the incline bench is taken, what can I swap it with?', 'get_workout', GW(PD), sc(P, PD)),

    # --- no tool ---
    item(264, '2026-11-03', [], 'hi, my friend told me to try this app', None, None, None),
    item(265, '2026-11-03', [
        U('Hi'),
        A('Hi! I\'m Wilo, your coach. What are your main goals: strength, muscle, fitness or rehab?', 'get_profile'),
    ], 'I just want to get fit, I haven’t worked out in years', None, None, None),
    item(266, '2026-11-03', [
        U('I just want to get fit, I haven’t worked out in years'),
        A('Got it. Any pain or injuries I should know about?'),
    ], 'Not really, my knees crack sometimes', None, None, None),
    item(267, '2026-11-03', [
        U('I cant do 10 pushups lol, can we do like 5'),
        A('Done. 3 sets of 5. Tap **Load**.', 'update_workout'),
    ], 'where is the load button', None, None, sc(NEW, NEW_DOC)),
    item(268, '2026-11-06', [], 'Bro I\'m so sore from yesterday', None, None, sc(B, BD)),
    item(269, '2026-11-13', [], 'Ok I\'m done with biceps, moving on', None, None, sc(M, MD)),
    item(270, '2026-11-09', [
        U('Uh, read me the workout, quick.'),
        A(f'Push pump: {summary(P)}', 'get_workout'),
    ], 'Got it, thanks', None, None, sc(P, PD)),
    item(271, '2026-11-02', [], 'Hmm', None, None, sc(S, SD)),
    item(272, '2026-11-01', [], 'Can you explain what a deload is', None, None, None),
    item(273, '2026-11-11', [], 'Can you see my heart rate', None, None, sc(K, KD)),

    # --- assign_workout ---
    item(274, '2026-11-02', [
        U('Nothing really, I like pushups I guess'),
        A(f'Ok, I\'ll start simple. First workout for tomorrow: {summary(NEW)}. Save?', 'workout_schema', 'assign_workout'),
    ], 'sure', 'assign_workout', {'workout': NEW, 'write': True}, None),
    item(275, '2026-11-08', [
        U('Plan tomorrow, shoulders'),
        A(f'Monday shoulders + biceps + rehab: {summary(S)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'swap sword raises for face pulls', 'assign_workout',
         {'workout': edit(S, rep('Sword raise', ex('Face pull', '3x12@25'))), 'write': False}, None),
    item(276, '2026-11-12', [
        U('Plan friday back day'),
        A(f'Friday back + hamstrings + triceps: {summary(B)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'Ya', 'assign_workout', {'workout': B, 'write': True}, None),
    item(277, '2026-11-12', [
        U('Plan friday back day'),
        A(f'Friday back + hamstrings + triceps: {summary(B)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'No hamstring stuff, my back is still tweaked', 'assign_workout',
         {'workout': edit(B, chain(rm('Double leg curls'), rm('Dumbbell RDL'))), 'write': False}, None),
    item(278, '2026-11-14', [
        U('give me a 20 min bodyweight thing for today, I\'m at home'),
        A('Pushups, squats, plank, glute bridge, 3 rounds?', 'get_profile'),
    ], 'ya', 'assign_workout', {'workout': workout('home-bw-nov-14', '2026-11-14', [
        ex('Pushups', '3x15'), ex('Bodyweight squat', '3x15'), ex('Plank', '3x45t'), ex('Glute bridge', '3x15')]), 'write': False}, None),

    # --- reads ---
    item(279, '2026-11-03', [], 'did my workout save', 'recent_completed', {'limit': 1}, sc(NEW, NEW_DOC)),
    item(280, '2026-11-09', [], 'Uh, can you check, uh, what I did for push last time?', 'recent_completed', {'limit': 5}, sc(P, PD)),
    item(281, '2026-11-06', [
        U('done'),
        A('Nice! How did it feel?'),
    ], 'good, back felt fine. did I hit everything', 'recent_completed', {'limit': 1}, sc(B, BD)),
    item(282, '2026-11-08', [], 'Whats coming up this week', 'recent_assigned', {'limit': 7}, None),
    item(283, '2026-11-05', [
        U('Hey'),
        A('Hey Thom! Chest + biceps today.'),
    ], 'For tomorrow take out the dips', 'recent_assigned', {'limit': 3}, sc(C, CD)),
    item(284, '2026-11-02', [], 'What did I lift for face pulls last time', 'exercise_history', {'name': 'Face pull', 'limit': 2}, sc(S, SD)),
    item(285, '2026-11-13', [], 'Am I getting stronger on tricep pushdowns', 'exercise_history', {'name': 'Tricep pushdown', 'limit': 10}, sc(M, MD)),
    item(286, '2026-11-09', [
        U('Can we add close grip bench'),
        A('Sure. How heavy?'),
    ], 'what did I do before', 'exercise_history', {'name': 'Close grip bench', 'limit': 2}, sc(P, PD)),
    item(287, '2026-11-08', [], 'Uh, I think I called it hammer press and hammer machine press, are those the same in your list?', 'exercise_names', {}, None),
    item(288, '2026-11-13', [], 'which exercises have I not done in a while', 'exercise_names', {}, None),

    # --- profile, schema, method ---
    item(289, '2026-11-02', [
        U('Not really, my knees crack sometimes'),
        A('Ok. Save "goal: get fit, knees crack sometimes" to your profile?'),
    ], 'yes', 'update_profile', {'plan': '- 2026-11-02: Goal: get fit. Hasn\'t trained in years.',
                                 'limitations': '- 2026-11-02: Knees crack sometimes, no pain.', 'write': False}, None),
    item(290, '2026-11-13', [
        U('I want to start doing chin-ups, its a goal of mine to do 10'),
        A('Love it. Add "goal: 10 chin-ups" to your plan?', 'get_profile'),
    ], 'ya', 'update_profile', {
        'plan': '- 2026-10-24: Goal: strength.\n- 2026-10-25: Weekly split: Mon shoulders + biceps + rehab, Tue legs + triceps, Wed cardio, Thu chest + biceps, Fri back + hamstrings + triceps, Sat cardio, Sun rest.\n- 2026-11-13: Goal: 10 chin-ups.',
        'write': False}, sc(M, MD)),
    item(291, '2026-11-02', [], 'hey can you make me my first workout', 'get_profile', {}, None),
    item(292, '2026-11-12', [
        U('Plan saturday, full body, something new'),
        A('Sure. Barbell, or machines only?', 'get_profile', 'recent_completed'),
    ], 'Machines only', 'workout_schema', {}, None),
    item(293, '2026-11-08', [
        U('Can you plan me a deload week'),
        A('Sure. Same split, about 60% of the weight?', 'get_profile', 'recent_completed'),
    ], 'Ya build it', 'workout_schema', {}, None),
    item(294, '2026-11-02', [
        U('Can you plan the week'),
        A('Sure, starting with Monday?', 'get_profile', 'recent_assigned'),
    ], 'ya write them all up', 'workout_schema', {}, None),
    item(295, '2026-11-14', [], 'How do you decide when to add weight', 'coaching_method', {}, None),

    # --- todos ---
    item(296, '2026-11-07', [], 'add laundry', 'add_todo', {'text': 'Laundry'}, None),
    item(297, '2026-11-07', [], 'Whats left on my list', 'list_todos', {}, None),
    item(298, '2026-11-07', [U('Whats left on my list'), A(TODOS, 'list_todos')],
         'meal prep is now saturday not sunday', 'update_todo', {'doc_id': 'k0Mb7RxEc3', 'due': '2026-11-07'}, None),
    item(299, '2026-11-07', [U('Whats left on my list'), A(TODOS, 'list_todos')],
         'remove the amazon one, I\'m keeping it', 'delete_todo', {'doc_id': 'Vs4Yh9PoL1'}, None),
    item(300, '2026-11-07', [U('Whats left on my list'), A(TODOS, 'list_todos')],
         'kill laundry from the list entirely', 'delete_todo', {'doc_id': 'Fg5Tn2WqZ8'}, None),
]

write(items, 251)
