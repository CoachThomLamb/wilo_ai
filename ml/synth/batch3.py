from lib import *
from base import *

S, SD = S2, S2_DOC
L, LD = L2, L2_DOC
C, CD = C2, C2_DOC
M, MD = ARMS, ARMS_DOC
K, KD = CARDIO, CARDIO_DOC
GW = lambda d: {'collection': 'assigned', 'doc_id': d}
UW = lambda d, w, write: {'collection': 'assigned', 'doc_id': d, 'workout': w, 'write': write}
TODOS = 'Open: 1. Dentist (Nov 12 14:00) [id Lq0vT7cBn2] 2. Renew gym membership [id 9sKe3RwPz1] 3. Groceries [id hY6uA2mDq8]'

items = [
    # --- update_workout (read already) ---
    item(101, '2026-11-09', [
        U('wat do i have'),
        A(f'Shoulders + biceps + rehab: {summary(S)}', 'recent_assigned'),
    ], 'Lateral raises after sword raises', 'update_workout', UW(SD, edit(S, mv('Lateral raise', 'Sword raise')), False), sc(S, SD)),
    item(102, '2026-11-09', [
        U('Lateral raises after sword raises'),
        A('Moving lateral raise after sword raise. Ok?', 'update_workout'),
    ], 'ok', 'update_workout', UW(SD, edit(S, mv('Lateral raise', 'Sword raise')), True), sc(S, SD)),
    item(103, '2026-11-10', [
        U('Uh, read me today\'s workout please.'),
        A(f'Legs + triceps: {summary(L)}', 'get_workout'),
    ], 'Um, the B stance lunges, my knee doesn\'t like them today. Can we do, uh, leg extensions instead?', 'update_workout',
         UW(LD, edit(L, rep('B-stance lunge', ex('Leg extension', '3x12@70'))), False), sc(L, LD)),
    item(104, '2026-11-12', [
        U('whats on'),
        A(f'Chest + biceps: {summary(C)}', 'recent_assigned'),
        U('k'),
        A('Have a good one.'),
    ], 'Dont have 20 min for the walk at the end, make it 10', 'update_workout',
         UW(CD, edit(C, rep('Treadmill', ex('Treadmill', 't600', '10 min easy walk.'))), False), sc(C, CD)),
    item(105, '2026-11-13', [
        U('read it'),
        A(f'Arms pump: {summary(M)}', 'get_workout'),
    ], 'swap preacher for spider curls same weight', 'update_workout',
         UW(MD, edit(M, rep('Preacher curl', ex('Spider curl', '3x12@30'))), False), sc(M, MD)),
    item(106, '2026-11-13', [
        U('swap preacher for spider curls same weight'),
        A('Swapping preacher curl for spider curl 3x12 @ 30. Ok?', 'update_workout'),
    ], 'Ya go', 'update_workout', UW(MD, edit(M, rep('Preacher curl', ex('Spider curl', '3x12@30'))), True), sc(M, MD)),
    item(107, '2026-11-11', [
        U('whats today'),
        A('Cardio: Treadmill 25 min.', 'recent_assigned'),
    ], 'Can you make it the bike instead of treadmill, the treadmills are all full', 'update_workout',
         UW(KD, edit(K, rep('Treadmill', ex('Bike', 't1500', '25 min.'))), False), sc(K, KD)),
    item(108, '2026-11-10', [
        U('Ya don’t ask just do it if it’s clear.'),
        A('Got it.'),
        U('whats left'),
        A(f'Left: {summary(L)}', 'recent_completed', 'get_workout'),
    ], 'kill the skull crushers', 'update_workout', UW(LD, edit(L, rm('Skull crusher')), True), sc(L, LD)),
    item(109, '2026-11-12', [
        U('whats on'),
        A(f'Chest + biceps: {summary(C)}', 'recent_assigned'),
        U('Swap the order of pec deck and the hammer press'),
        A('Pec deck before the hammer press now. Tap **Load**.', 'update_workout'),
    ], 'Also add a 4th set to pec deck', 'update_workout',
         UW(CD, edit(C, chain(swap('Pec deck', 'Hammer machine press'), resets('Pec deck', '4x12@100'))), False), sc(C, CD)),
    item(110, '2026-11-09', [
        U('wat do i have'),
        A(f'Shoulders + biceps + rehab: {summary(S)}', 'recent_assigned'),
        U('Shoulder feels great today'),
        A('Nice. Want to push the press up to 20?'),
    ], 'Yes 20', 'update_workout', UW(SD, edit(S, resets('Hammer seated', '2x12@20 RL')), False), sc(S, SD)),

    # --- get_workout ---
    item(111, '2026-11-13', [], 'preacher bench is taken change it', 'get_workout', GW(MD), sc(M, MD)),
    item(112, '2026-11-10', [
        U('Hey'),
        A('Hey Thom! Legs + triceps is loaded.'),
    ], 'Can you add calf raises at the end', 'get_workout', GW(LD), sc(L, LD)),
    item(113, '2026-11-12', [], 'Um, I\'m gonna skip the dead hangs today, my grip is shot.', 'get_workout', GW(CD), sc(C, CD)),
    item(114, '2026-11-11', [], 'make it 30 min instead', 'get_workout', GW(KD), sc(K, KD)),

    # --- no tool ---
    item(115, '2026-11-13', [], 'how many sets have I done today', 'recent_completed', {'limit': 1}, sc(M, MD)),
    item(116, '2026-11-09', [], 'Ok thanks bye', None, None, sc(S, SD)),
    item(117, '2026-11-10', [
        U('kill the skull crushers'),
        A('Done. Skull crushers are out. Tap **Load**.', 'update_workout'),
    ], '👍', None, None, sc(L, LD)),
    item(118, '2026-11-12', [], 'Can I superset the curls with something', None, None, sc(C, CD)),
    item(119, '2026-11-08', [], 'What muscles does the meadows row hit', None, None, None),
    item(120, '2026-11-13', [
        U('read it'),
        A(f'Arms pump: {summary(M)}', 'get_workout'),
    ], 'Sounds good', None, None, sc(M, MD)),
    item(121, '2026-11-10', [
        U('Uh, read me today\'s workout please.'),
        A(f'Legs + triceps: {summary(L)}', 'get_workout'),
        U('Um, the B stance lunges, my knee doesn\'t like them today.'),
        A('Want to swap them for leg extensions, or just drop them?'),
    ], 'Let me think about it, I\'ll do leg press first', None, None, sc(L, LD)),
    item(122, '2026-11-11', [], 'Should I do cardio before or after weights generally', None, None, sc(K, KD)),
    item(123, '2026-11-08', [], 'test', None, None, None),
    item(124, '2026-11-09', [
        U('Lateral raises after sword raises'),
        A('Moving lateral raise after sword raise. Ok?', 'update_workout'),
    ], 'Wait what are sword raises again', None, None, sc(S, SD)),
    item(125, '2026-11-12', [], 'Uh, my phone is about to die, I\'ll talk to you later.', None, None, sc(C, CD)),

    # --- assign_workout ---
    item(126, '2026-11-12', [
        U('Plan friday, I want an arm day'),
        A(f'Arms pump for Friday: {summary(M)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'Ya', 'assign_workout', {'workout': M, 'write': True}, None),
    item(127, '2026-11-12', [
        U('Plan friday, I want an arm day'),
        A(f'Arms pump for Friday: {summary(M)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'no treadmill and add pushups at the end 2 sets', 'assign_workout',
         {'workout': edit(M, chain(rm('Treadmill'), ins(None, ex('Pushups', '2x15')))), 'write': False}, None),
    item(128, '2026-11-08', [
        U('Plan next week same split'),
        A(f'Monday shoulders: {summary(S)}. Save?', 'get_profile', 'recent_completed', 'recent_assigned', 'assign_workout'),
    ], 'Yes', 'assign_workout', {'workout': S, 'write': True}, None),
    item(129, '2026-11-08', [
        U('Yes'),
        A(f'Monday is saved. Tuesday legs + triceps: {summary(L)}. Save?', 'assign_workout', 'assign_workout'),
    ], 'Ya and do the same for thursday chest', 'assign_workout', {'workout': L, 'write': True}, None),
    item(130, '2026-11-10', [
        U('Plan wednesday'),
        A('Wednesday is cardio. 25 min treadmill again?', 'get_profile', 'recent_assigned'),
    ], 'Do 20 min bike and 10 min treadmill', 'assign_workout', {'workout': workout('Cardio', '2026-11-11', [
        ex('Bike', 't1200', '20 min.'), ex('Treadmill', 't600', '10 min easy walk.')]), 'write': False}, None),
    item(131, '2026-11-11', [
        U('Can you make me a hotel gym workout for tomorrow, just dumbbells up to 50'),
        A('Sure. Full body, around 45 min?', 'get_profile', 'recent_completed'),
    ], 'Ya perfect', 'assign_workout', {'workout': workout('hotel-db-nov-12', '2026-11-12', [
        ex('Dead hang', '2x45t'), ex('Goblet squat', '3x12@50'), ex('Dumbbell RDL', '3x10@40'),
        ex('Dumbbell bench press', '3x10@45'), ex('One arm row', '3x10@45 RL'), ex('Dumbbell curl', '3x12@25'),
        ex('Pushups', '2x15')]), 'write': False}, None),
    item(132, '2026-11-11', [
        U('Ya perfect'),
        A('Hotel workout: 1. Dead hang 2x45s 2. Goblet squat 3x12 @ 50 3. Dumbbell RDL 3x10 @ 40 4. Dumbbell bench press 3x10 @ 45 5. One arm row 3x10 @ 45 6. Dumbbell curl 3x12 @ 25 7. Pushups 2x15. Save?', 'assign_workout'),
    ], 'save it', 'assign_workout', {'workout': workout('hotel-db-nov-12', '2026-11-12', [
        ex('Dead hang', '2x45t'), ex('Goblet squat', '3x12@50'), ex('Dumbbell RDL', '3x10@40'),
        ex('Dumbbell bench press', '3x10@45'), ex('One arm row', '3x10@45 RL'), ex('Dumbbell curl', '3x12@25'),
        ex('Pushups', '2x15')]), 'write': True}, None),

    # --- reads ---
    item(133, '2026-11-10', [], 'What was the last thing I did monday', 'recent_completed', {'limit': 2}, sc(L, LD)),
    item(134, '2026-11-13', [
        U('done for today'),
        A('Nice! Want a quick look at how it went?'),
    ], 'ya whatd i miss', 'recent_completed', {'limit': 1}, sc(M, MD)),
    item(135, '2026-11-14', [], 'Uh, how was my week overall, did I hit everything?', 'recent_completed', {'limit': 7}, None),
    item(136, '2026-11-08', [], 'Do I have anything planned for tomorrow yet', 'recent_assigned', {'limit': 3}, None),
    item(137, '2026-11-11', [
        U('Hi'),
        A('Hi Thom! Cardio today.'),
    ], 'For friday’s workout can you drop the dips', 'recent_assigned', {'limit': 5}, sc(K, KD)),
    item(138, '2026-11-13', [], 'whats my best on barbell curl', 'exercise_history', {'name': 'Barbell curl', 'limit': 10}, sc(M, MD)),
    item(139, '2026-11-10', [
        U('Add calf raises at the end'),
        A('Sure, how many sets and what weight?'),
    ], 'Uh whatever I did before', 'exercise_history', {'name': 'Calf raise', 'limit': 2}, sc(L, LD)),
    item(140, '2026-11-12', [], 'when did I last do pec deck', 'exercise_history', {'name': 'Pec deck', 'limit': 1}, sc(C, CD)),
    item(141, '2026-11-09', [], 'I think I\'ve logged sword raises under a couple different names, can you check', 'exercise_names', {}, sc(S, SD)),
    item(142, '2026-11-12', [
        U('I really like the spider curls, I want them more often'),
        A('Got it. Add that to your preferences?', 'get_profile'),
    ], 'Ya', 'update_profile', {
        'preferences': '- 2026-10-24: Likes dead hangs (help the shoulder a lot), sled dragging, walking/treadmill.\n- 2026-10-24: Decline front raises made both shoulders feel amazing: do them a lot more.\n- 2026-11-12: Likes spider curls. Program them more often.',
        'write': False}, sc(C, CD)),
    item(143, '2026-11-10', [], 'my knee has been bugging me on lunges, remember that', 'get_profile', {}, sc(L, LD)),
    item(144, '2026-11-10', [
        U('my knee has been bugging me on lunges, remember that'),
        A('Here\'s the change, limitations + "2026-11-10: Knee bugs on lunges." Save?', 'get_profile', 'update_profile'),
    ], 'yup', 'update_profile', {
        'limitations': '- 2026-10-24: Torn quadriceps. Isometrics and walking help.\n- 2026-10-24: Right hamstring twinges on heavy hinges.\n- 2026-11-10: Knee bugs on lunges.',
        'write': True}, sc(L, LD)),
    item(145, '2026-11-11', [
        U('Can you make me a hotel gym workout for tomorrow'),
        A('Sure. What equipment do they have?'),
    ], 'dumbbells up to 50 and a bench, make it full body', 'workout_schema', {}, None),
    item(146, '2026-11-08', [], 'Wilo how should we approach the next block, I want to get stronger', 'coaching_method', {}, None),

    # --- todos ---
    item(147, '2026-11-09', [], 'Add dentist on the 12th at 2pm', 'add_todo', {'text': 'Dentist', 'due': '2026-11-12 14:00'}, sc(S, SD)),
    item(148, '2026-11-10', [], 'what’s on my todo list', 'list_todos', {}, None),
    item(149, '2026-11-10', [U('what’s on my todo list'), A(TODOS, 'list_todos')],
         'Renewed the gym membership, mark it done', 'update_todo', {'doc_id': '9sKe3RwPz1', 'done': True}, None),
    item(150, '2026-11-10', [U('what’s on my todo list'), A(TODOS, 'list_todos')],
         'delete groceries I did it already and I don’t need it there', 'delete_todo', {'doc_id': 'hY6uA2mDq8'}, None),
]

write(items, 101)
