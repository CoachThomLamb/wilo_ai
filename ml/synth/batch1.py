from lib import *
from base import *

S, SD = SHOULDERS, SHOULDERS_DOC
L, LD = LEGS, LEGS_DOC
C, CD = CHEST, CHEST_DOC
B, BD = BACK, BACK_DOC
GW = lambda d: {'collection': 'assigned', 'doc_id': d}
UW = lambda d, w, write: {'collection': 'assigned', 'doc_id': d, 'workout': w, 'write': write}

items = [
    # --- mid-workout, workout already read in this chat → update_workout ---
    item(1, '2026-11-03', [
        U('whats on for today'),
        A(f'Legs + triceps: {summary(L)}', 'recent_assigned'),
    ], 'hack squat is taken some guy has been on it forever. swap for leg extension 3x12',
         'update_workout', UW(LD, edit(L, rep('Hack squat', ex('Leg extension', '3x12@70'))), False), sc(L, LD)),

    item(2, '2026-11-03', [
        U('hack squat is taken some guy has been on it forever. swap for leg extension 3x12'),
        A('Swapping hack squat for leg extension 3x12 @ 70, ok?', 'update_workout'),
    ], 'ya do it', 'update_workout',
         UW(LD, edit(L, rep('Hack squat', ex('Leg extension', '3x12@70'))), True), sc(L, LD)),

    item(3, '2026-11-02', [
        U('Can you read me my workout'),
        A(f'Today: {summary(S)}', 'get_workout'),
        U('ok thx'),
        A('Have a good one. Tap **Load** if you change anything.'),
    ], 'Shoulder is pinching on the press. Drop it and add an extra set of dead hangs', 'update_workout',
         UW(SD, edit(S, chain(rm('Hammer seated'), resets('Dead hang', '3x45t'))), False), sc(S, SD)),

    item(4, '2026-11-05', [
        U('Show me what’s left'),
        A(f'Still to go: {summary(C)}', 'recent_completed', 'get_workout'),
        U('Kk'),
        A('Go get it.'),
    ], 'pec deck is broken. Do cable flys instead same sets', 'update_workout',
         UW(CD, edit(C, rep('Pec deck', ex('Cable fly', '3x12@30'))), False), sc(C, CD)),

    item(5, '2026-11-06', [
        U('Ya don’t ask just do it if it’s clear.'),
        A('Got it. Clear changes go straight in.', 'update_workout'),
        U('Put Meadows rows after the pulldown'),
        A('Done. Meadows row now comes after the pulldown. Tap **Load**.', 'update_workout'),
    ], 'Drop the dip machine I’m cooked', 'update_workout',
         UW(BD, edit(B, chain(mv('Meadows', 'Hammer machine pulldown'), rm('Dip machine'))), True), sc(B, BD)),

    item(6, '2026-11-03', [
        U('whats my workout'),
        A(f'Legs + triceps: {summary(L)}', 'recent_assigned'),
        U('leg press felt easy last week'),
        A('Last time all 3x10 at 200 got done, so you can go up. Want 210?'),
    ], 'Ya make it 210', 'update_workout',
         UW(LD, edit(L, resets('Leg press', '3x10@210')), False), sc(L, LD)),

    item(7, '2026-11-02', [
        U('Load it up'),
        A(f'Today is shoulders + biceps + rehab: {summary(S)}', 'get_workout'),
    ], 'skip the massage today no time', 'update_workout',
         UW(SD, edit(S, rm('Massage')), False), sc(S, SD)),

    item(8, '2026-11-05', [
        U('what’s today'),
        A(f'Chest + biceps: {summary(C)}', 'recent_assigned'),
        U('Can you add uh hammer curls after the barbell curls'),
        A('Last hammer curls were 3x10 @ 25. Add those after barbell curl, ok?', 'exercise_history', 'update_workout'),
    ], 'Yep', 'update_workout',
         UW(CD, edit(C, ins('Barbell curl', ex('Hammer curl', '3x10@25'))), True), sc(C, CD)),

    item(9, '2026-11-06', [
        U('Hi'),
        A('Hi Thom! Friday is back + hamstrings + triceps. It\'s loaded.', 'recent_assigned'),
        U('what’s in it'),
        A(f'{summary(B)}', 'get_workout'),
    ], 'hamstring is tight today. Take out the RDLs and the leg curls just do upper', 'update_workout',
         UW(BD, edit(B, chain(rm('Dumbbell RDL'), rm('Double leg curls'))), False), sc(B, BD)),

    item(10, '2026-11-03', [
        U('Read me the rest'),
        A(f'Left: {summary(L)}', 'recent_completed', 'get_workout'),
        U('Kk'),
        A('Tap **Load** if anything changes.'),
    ], 'Can we move skull crusher push-ups to right after leg press I wanna do them while I’m on the floor', 'update_workout',
         UW(LD, edit(L, mv('Skull crusher', 'Leg press')), False), sc(L, LD)),

    item(11, '2026-11-05', [
        U('swap the barbell curls for ez bar'),
        A('Swapping barbell curl for EZ bar curl, same 3x10 @ 45. Ok?', 'update_workout'),
    ], 'Ship it', 'update_workout',
         UW(CD, edit(C, rep('Barbell curl', ex('EZ bar curl', '3x10@45'))), True), sc(C, CD)),

    item(12, '2026-11-02', [
        U('whats my workout'),
        A(f'Shoulders + biceps + rehab: {summary(S)}', 'get_workout'),
        U('Uh the sword raises, they’re really hard on the left side'),
        A('Want me to drop the weight to 3 or take them out?'),
    ], 'Drop to 3', 'update_workout',
         UW(SD, edit(S, resets('Sword raise', '3x6@3 RL')), False), sc(S, SD)),

    # --- mid-workout, first mention, not read yet → get_workout ---
    item(13, '2026-11-03', [], 'hack squats taken. what else can i do', 'get_workout', GW(LD), sc(L, LD)),
    item(14, '2026-11-02', [
        U('Hey'),
        A('Hey! What do you need?'),
    ], 'Can you switch the lateral raises to cable lateral raises', 'get_workout', GW(SD), sc(S, SD)),
    item(15, '2026-11-05', [], 'Pec deck is out of order. Swap it for something', 'get_workout', GW(CD), sc(C, CD)),
    item(16, '2026-11-06', [], 'Add uh like 10 min of cardio at the end please', 'get_workout', GW(BD), sc(B, BD)),
    item(17, '2026-11-03', [
        U('Morning'),
        A('Morning Thom. Legs + triceps is loaded. How\'s the quad?'),
    ], 'Quads fine. Make the leg press 4 sets instead of 3', 'get_workout', GW(LD), sc(L, LD)),
    item(18, '2026-11-02', [], 'shoulder hurts on the press skip it', 'get_workout', GW(SD), sc(S, SD)),

    # --- no tool ---
    item(19, '2026-11-03', [], 'Hey how’s it going', None, None, sc(L, LD)),
    item(20, '2026-11-05', [
        U('pec deck is broken. Do cable flys instead same sets'),
        A('Swapping pec deck for cable fly 3x12 @ 30, ok?', 'update_workout'),
        U('Ya'),
        A('Done. Tap **Load**.', 'update_workout'),
    ], 'Thanks', None, None, sc(C, CD)),
    item(21, '2026-11-06', [], 'Should I go heavier on rows if the last set felt easy', None, None, sc(B, BD)),
    item(22, '2026-11-02', [
        U('Can you read me my workout'),
        A(f'Today: {summary(S)}', 'get_workout'),
    ], 'Uh, wait, hold on. One sec', None, None, sc(S, SD)),
    item(23, '2026-10-30', [], 'How do I put Wilo on my home screen on iPhone', None, None, None),
    item(24, '2026-11-03', [
        U('hack squat is taken some guy has been on it forever. swap for leg extension 3x12'),
        A('Swapping hack squat for leg extension 3x12 @ 70, ok?', 'update_workout'),
    ], 'actually no wait he’s getting off it. leave it', None, None, sc(L, LD)),
    item(25, '2026-11-05', [], 'what’s the cue for serratus shrug again', None, None, sc(C, CD)),
    item(26, '2026-11-01', [], 'Are you there', None, None, None),
    item(27, '2026-11-06', [
        U('Drop the dip machine I’m cooked'),
        A('Done. Dip machine is out. Tap **Load**.', 'update_workout'),
    ], 'Good workout today felt strong', None, None, sc(B, BD)),
    item(28, '2026-11-02', [], 'is it bad to train shoulders two days in a row', None, None, sc(S, SD)),

    # --- plan / assign ---
    item(29, '2026-11-04', [
        U('Can you plan tomorrow'),
        A('Thursday is chest + biceps. Same as last Thursday with small bumps where you finished everything?', 'get_profile', 'recent_completed'),
    ], 'Ya but no treadmill at the end I’ll walk home', 'assign_workout',
         {'workout': edit(C, rm('Treadmill')), 'write': False}, None),
    item(30, '2026-11-04', [
        U('Can you plan tomorrow'),
        A('Thursday is chest + biceps. Same as last Thursday with small bumps where you finished everything?', 'get_profile', 'recent_completed'),
        U('Ya but no treadmill at the end I’ll walk home'),
        A(f'Draft for Thursday: {summary(edit(C, rm("Treadmill")))}. Save it?', 'assign_workout'),
    ], 'Save', 'assign_workout', {'workout': edit(C, rm('Treadmill')), 'write': True}, None),
    item(31, '2026-11-03', [
        U('plan wednesday'),
        A('Wednesday is cardio on your split. 25 minutes again?', 'get_profile', 'recent_assigned'),
    ], 'Ya 25 on the treadmill', 'assign_workout',
         {'workout': workout('Cardio', '2026-11-04', [ex('Treadmill', 't1500', '25 min.')]), 'write': False}, None),
    item(32, '2026-11-08', [
        U('need a quick one today 30 min tops'),
        A('Sunday is usually rest. Want a short shoulder rehab block: dead hang, serratus shrug, scap pull-ups, decline front raise, 10 min walk?', 'get_profile', 'recent_completed'),
    ], 'Perfect put it in', 'assign_workout', {'workout': workout('shoulder-rehab-nov-8', '2026-11-08', [
        ex('Dead hang', '2x45t', '~45s each. Opens the shoulder.'),
        ex('Serratus shrug', '3x10'),
        ex('Scapular pull-up', '2x5'),
        ex('Decline front raise', '3x6@5'),
        ex('Treadmill', 't600', '10 min easy walk.'),
    ]), 'write': True}, None),
    item(33, '2026-11-01', [
        U('Monday is shoulders right'),
        A('Yes, Monday is shoulders + biceps + rehab. Same as last Monday?', 'get_profile'),
        U('Same but add lateral raises 3x12 at 5'),
        A(f'Draft: {summary(S)}. Save?', 'assign_workout'),
    ], 'Yup', 'assign_workout', {'workout': S, 'write': True}, None),

    # --- reads ---
    item(34, '2026-11-02', [], 'how did i do on friday', 'recent_completed', {'limit': 3}, None),
    item(35, '2026-11-06', [
        U('done'),
        A('Nice. Want to go over it?'),
    ], 'Ya how’d I do', 'recent_completed', {'limit': 1}, sc(B, BD)),
    item(36, '2026-11-03', [], 'What have I done this week so far', 'recent_completed', {'limit': 5}, None),
    item(37, '2026-11-03', [], 'whats planned for the rest of the week', 'recent_assigned', {'limit': 7}, None),
    item(38, '2026-11-04', [
        U('hi'),
        A('Hi Thom! Wednesday is cardio. Want me to plan it?'),
    ], 'I think I already have something for today', 'recent_assigned', {'limit': 3}, None),
    item(39, '2026-11-05', [], 'What did I bench last time', 'exercise_history', {'name': 'bench press', 'limit': 3}, sc(C, CD)),
    item(40, '2026-11-03', [
        U('Can you add Bulgarian split squats after crane plane'),
        A('Sure. How many sets?'),
    ], 'Whatever I did last time', 'exercise_history', {'name': 'Bulgarian split squat', 'limit': 2}, sc(L, LD)),
    item(41, '2026-11-06', [], 'how much did I row on meadows last couple times', 'exercise_history',
         {'name': 'Meadows row', 'limit': 2}, sc(B, BD)),
    item(42, '2026-10-31', [], 'have I ever done face pulls or something like that, maybe I called it rope pulls', 'exercise_names', {}, None),
    item(43, '2026-11-02', [
        U('Shoulder is pinching on the press. Drop it and add an extra set of dead hangs'),
        A('Done. Press is out, dead hangs are 3x45s. Tap **Load**.', 'update_workout'),
        U('Kk'),
        A('Want me to note the press pinch in your profile?'),
    ], 'Ya', 'get_profile', {}, sc(S, SD)),
    item(44, '2026-11-02', [
        U('Ya'),
        A('Here\'s the change: limitations + "2026-11-02: Hammer seated shoulder press pinched the shoulder. Skip it for now." Save?', 'get_profile', 'update_profile'),
    ], 'Save', 'update_profile', {
        'limitations': '- 2026-10-24: Torn quadriceps. Isometrics and walking help.\n- 2026-10-24: Right hamstring twinges on heavy hinges.\n- 2026-11-02: Hammer seated shoulder press pinched the shoulder. Skip it for now.',
        'write': True}, sc(S, SD)),
    item(45, '2026-10-30', [], 'From now on I want cardio on saturdays to be 30 min not 25', 'get_profile', {}, None),
    item(46, '2026-10-31', [
        U('I hate lunges by the way, never put them in again'),
        A('Got it. Add "no lunges" to your preferences?', 'get_profile'),
    ], 'yes please', 'update_profile', {
        'preferences': '- 2026-10-24: Likes dead hangs (help the shoulder a lot), sled dragging, walking/treadmill.\n- 2026-10-24: Decline front raises made both shoulders feel amazing: do them a lot more.\n- 2026-10-31: Hates lunges. Never program them.',
        'write': False}, None),

    # --- todos and misc ---
    item(47, '2026-11-02', [], 'add a todo, call the physio tomorrow morning', 'add_todo',
         {'text': 'Call the physio', 'due': '2026-11-03 09:00'}, None),
    item(48, '2026-11-02', [], 'what do I have on my list today', 'list_todos', {}, None),
    item(49, '2026-11-02', [
        U('what do I have on my list today'),
        A('Open: 1. Call the physio (tomorrow 9:00) [id 7fQm2LxKp0] 2. Haircut [id Rr81bcZt4e] 3. Bank machine [id 0dXwq9PiUv]', 'list_todos'),
    ], 'got the haircut done check that off', 'update_todo', {'doc_id': 'Rr81bcZt4e', 'done': True}, None),
    item(50, '2026-11-04', [
        U('Can you plan tomorrow from scratch, new exercises for chest'),
        A('Sure. Want to keep the shoulder warm-up first?', 'get_profile', 'recent_completed'),
    ], 'Ya keep the warm up and then go', 'workout_schema', {}, None),
]

write(items, 1)
