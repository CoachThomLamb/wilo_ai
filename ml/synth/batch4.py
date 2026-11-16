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
TODOS = 'Open: 1. Pick up dry cleaning (today) [id c4Rr8NnXe0] 2. Call mom [id Wb2Kp7sQa3] 3. Book physio (Nov 4) [id 5gHt1ZyLm9]'

items = [
    # --- update_workout ---
    item(151, '2026-11-06', [
        U('Ok so whats today again'),
        A(f'Back + hamstrings + triceps: {summary(B)}', 'get_workout'),
    ], 'Hammer pulldown is broken, out of order sign on it. Do lat pulldown instead same weight', 'update_workout',
         UW(BD, edit(B, rep('Hammer machine pulldown', ex('Lat pulldown', '3x10@120'))), False), sc(B, BD)),
    item(152, '2026-11-06', [
        U('Hammer pulldown is broken. Do lat pulldown instead same weight'),
        A('Swapping hammer pulldown for lat pulldown 3x10 @ 120. Ok?', 'update_workout'),
    ], 'Yup yup', 'update_workout', UW(BD, edit(B, rep('Hammer machine pulldown', ex('Lat pulldown', '3x10@120'))), True), sc(B, BD)),
    item(153, '2026-11-07', [
        U('read me the plan'),
        A(f'Lower-body rehab: {summary(R)}', 'get_workout'),
        U('The leg extension is at 70?'),
        A('Yes, 3x15 @ 70.'),
    ], 'Too light, make it 80', 'update_workout', UW(RD, edit(R, resets('Leg extension', '3x15@80')), False), sc(R, RD)),
    item(154, '2026-11-09', [
        U('What do I got today?'),
        A(f'Push pump: {summary(P)}', 'recent_assigned'),
    ], 'Uh, take out the dead hangs and start with the hammer press, I already warmed up.', 'update_workout',
         UW(PD, edit(P, rm('Dead hang')), False), sc(P, PD)),
    item(155, '2026-11-02', [
        U('whats today'),
        A(f'Shoulders + biceps + rehab: {summary(S)}', 'recent_assigned'),
        U('Shoulder is pinching on the press'),
        A('Want to drop it, or go lighter at 10?'),
    ], 'Lighter', 'update_workout', UW(SD, edit(S, resets('Hammer seated', '2x12@10 RL')), False), sc(S, SD)),
    item(156, '2026-11-03', [
        U('Ya don’t ask just do it if it’s clear.'),
        A('Got it. Clear changes go straight in.'),
        U('Whats left'),
        A(f'Left: {summary(L)}', 'recent_completed', 'get_workout'),
    ], 'swap crane plane and leg press', 'update_workout', UW(LD, edit(L, swap('Crane-plane', 'Leg press')), True), sc(L, LD)),
    item(157, '2026-11-05', [
        U('Uh, pull up the workout'),
        A(f'Chest + biceps: {summary(C)}', 'get_workout'),
    ], 'So I don\'t wanna do the curls at the end today, I\'m doing arms tomorrow. Just take both out.', 'update_workout',
         UW(CD, edit(C, chain(rm('Barbell curl'), rm('Free motion'))), False), sc(C, CD)),
    item(158, '2026-11-05', [
        U('So I don\'t wanna do the curls at the end today. Just take both out.'),
        A('Taking out barbell curl and the cable curl. Ok?', 'update_workout'),
    ], 'Ya', 'update_workout', UW(CD, edit(C, chain(rm('Barbell curl'), rm('Free motion'))), True), sc(C, CD)),
    item(159, '2026-11-07', [
        U('read me the plan'),
        A(f'Lower-body rehab: {summary(R)}', 'get_workout'),
    ], 'add 5 min treadmill at the start, its cold in here', 'update_workout',
         UW(RD, edit(R, ins('', TREAD5())), False), sc(R, RD)),
    item(160, '2026-11-09', [
        U('What do I got today?'),
        A(f'Push pump: {summary(P)}', 'recent_assigned'),
        U('Dips after pushdowns'),
        A('Dip machine now comes after tricep pushdown. Tap **Load**.', 'update_workout'),
    ], 'Kk and make pushups 3 sets', 'update_workout',
         UW(PD, edit(P, chain(mv('Dip machine', 'Tricep pushdown'), resets('Pushups', '3x15'))), False), sc(P, PD)),

    # --- get_workout ---
    item(161, '2026-11-06', [], 'out of order sign on the hammer pulldown. what now', 'get_workout', GW(BD), sc(B, BD)),
    item(162, '2026-11-09', [
        U('Morning'),
        A('Morning Thom! Push pump is loaded.'),
    ], 'Put the pushups first as a warm up', 'get_workout', GW(PD), sc(P, PD)),
    item(163, '2026-11-02', [], 'Uh, so can we, um, change the lateral raises to the machine?', 'get_workout', GW(SD), sc(S, SD)),
    item(164, '2026-11-07', [], 'drop the walk at the end', 'get_workout', GW(RD), sc(R, RD)),

    # --- no tool ---
    item(165, '2026-11-06', [], 'Lol the gym is packed today', None, None, sc(B, BD)),
    item(166, '2026-11-07', [
        U('add 5 min treadmill at the start, its cold in here'),
        A('Done. 5 min treadmill at the start. Tap **Load**.', 'update_workout'),
    ], 'Thanks man', None, None, sc(R, RD)),
    item(167, '2026-11-05', [], 'Uh, is it okay to do curls two days in a row?', None, None, sc(C, CD)),
    item(168, '2026-11-09', [
        U('Uh, take out the dead hangs and start with the hammer press, I already warmed up.'),
        A('Taking out dead hangs. Ok?', 'update_workout'),
    ], 'Hmm actually I’ll still do them, never mind', None, None, sc(P, PD)),
    item(169, '2026-11-01', [], 'good morning', None, None, None),
    item(170, '2026-11-03', [], 'what does B stance mean', None, None, sc(L, LD)),
    item(171, '2026-11-02', [
        U('whats today'),
        A(f'Shoulders + biceps + rehab: {summary(S)}', 'recent_assigned'),
    ], 'Ok cool, heading to the gym now', None, None, sc(S, SD)),
    item(172, '2026-11-06', [], 'Do you think I should take a deload week soon', None, None, None),
    item(173, '2026-10-31', [], 'Hey uh, can you, like, can you hear me, is this working?', None, None, None),
    item(174, '2026-11-04', [
        U('Can you plan tomorrow'),
        A('Thursday is chest + biceps. Same as last Thursday?', 'get_profile', 'recent_completed'),
    ], 'Hmm let me think about what I want, I’ll get back to you', None, None, None),

    # --- assign_workout ---
    item(175, '2026-11-05', [
        U('plan tomorrow'),
        A(f'Friday is back + hamstrings + triceps: {summary(B)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'Looks good save', 'assign_workout', {'workout': B, 'write': True}, None),
    item(176, '2026-11-05', [
        U('plan tomorrow'),
        A(f'Friday is back + hamstrings + triceps: {summary(B)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'add dragging at the end 6 at 135', 'assign_workout',
         {'workout': edit(B, ins(None, ex('Dragging', '6x1@135', 'Drag 6, pull 2.'))), 'write': False}, None),
    item(177, '2026-11-02', [
        U('Can you plan legs for tomorrow'),
        A('Same as last Tuesday with leg press up to 200 since you finished all of 180?', 'get_profile', 'recent_completed'),
    ], 'Ya that works', 'assign_workout', {'workout': L, 'write': False}, None),
    item(178, '2026-11-02', [
        U('Ya that works'),
        A(f'Tuesday draft: {summary(L)}. Save?', 'assign_workout'),
    ], 'ship it', 'assign_workout', {'workout': L, 'write': True}, None),
    item(179, '2026-11-08', [
        U('Plan me something for today, I have like 40 min'),
        A('Sunday is rest, but a short push pump fits. Hammer press, incline DB, cable fly, dips, pushdowns, pushups?', 'get_profile', 'recent_completed'),
    ], 'Ya but no dips', 'assign_workout', {'workout': workout('push-pump-nov-8', '2026-11-08', [
        ex('Hammer machine press', '4x10@90', 'Partial range, pain-free.'), ex('Incline dumbbell press', '3x10@40'),
        ex('Cable fly', '3x12@30'), ex('Tricep pushdown', '3x12@40'), ex('Pushups', '2x15')]), 'write': False}, None),
    item(180, '2026-11-01', [
        U('Uh, okay, so I want Monday to be shoulders and biceps with the rehab like usual.'),
        A('Same as last Monday, plus lateral raises?', 'get_profile', 'recent_completed'),
    ], 'Yeah and put the massage after the treadmill', 'assign_workout', {'workout': S, 'write': False}, None),
    item(181, '2026-11-06', [
        U('tomorrow I want to do the lower body rehab'),
        A(f'Saturday lower-body rehab: {summary(R)}. Save?', 'get_profile', 'recent_completed', 'assign_workout'),
    ], 'yes please', 'assign_workout', {'workout': R, 'write': True}, None),

    # --- reads ---
    item(182, '2026-11-04', [], 'how did legs go yesterday', 'recent_completed', {'limit': 1}, None),
    item(183, '2026-11-06', [], 'I finished, did it save?', 'recent_completed', {'limit': 1}, sc(B, BD)),
    item(184, '2026-11-08', [
        U('Hi'),
        A('Hi Thom! Want to plan next week?'),
    ], 'Ya first look at what I did this week', 'recent_completed', {'limit': 7}, None),
    item(185, '2026-11-02', [], 'What’s on for tomorrow?', 'recent_assigned', {'limit': 3}, sc(S, SD)),
    item(186, '2026-11-03', [
        U('Hey'),
        A('Hey Thom! Legs + triceps today.'),
    ], 'Can you push friday’s back workout to saturday', 'recent_assigned', {'limit': 7}, sc(L, LD)),
    item(187, '2026-11-07', [], 'What did I do on leg extensions the last few times', 'exercise_history', {'name': 'Leg extension', 'limit': 3}, sc(R, RD)),
    item(188, '2026-11-09', [
        U('Can we add incline bench'),
        A('Sure. Barbell or dumbbell?'),
    ], 'Dumbbell, what did I do last time', 'exercise_history', {'name': 'Incline dumbbell press', 'limit': 2}, sc(P, PD)),
    item(189, '2026-11-06', [], 'how heavy have I gone on RDLs', 'exercise_history', {'name': 'Dumbbell RDL', 'limit': 10}, sc(B, BD)),
    item(190, '2026-11-01', [], 'Did I ever log anything like a farmer carry? Maybe called it walks or something', 'exercise_names', {}, None),
    item(191, '2026-11-02', [], 'Hey new here, can you make me a workout', 'get_profile', {}, None),
    item(192, '2026-11-06', [
        U('I want to start doing cardio after every workout, 10 min'),
        A('Got it. Add that to your plan?', 'get_profile'),
    ], 'Ya save it', 'update_profile', {
        'plan': '- 2026-10-24: Goal: strength.\n- 2026-10-25: Weekly split: Mon shoulders + biceps + rehab, Tue legs + triceps, Wed cardio, Thu chest + biceps, Fri back + hamstrings + triceps, Sat cardio, Sun rest.\n- 2026-11-06: 10 min cardio after every workout.',
        'write': False}, sc(B, BD)),
    item(193, '2026-11-04', [
        U('Can you plan tomorrow'),
        A('Sure. Same chest day as last week, or something new?', 'get_profile', 'recent_completed'),
    ], 'Something new, mix it up', 'workout_schema', {}, None),
    item(194, '2026-11-01', [], 'I want to plan out a whole new 4 week block, where do we start', 'coaching_method', {}, None),

    # --- todos ---
    item(195, '2026-11-03', [], 'Add a todo get new lifting shoes, no rush', 'add_todo', {'text': 'Get new lifting shoes'}, sc(L, LD)),
    item(196, '2026-11-03', [], 'Remind me to stretch tonight at 9', 'add_todo', {'text': 'Stretch', 'due': '2026-11-03 21:00'}, None),
    item(197, '2026-11-03', [], 'whats on my todos, including the done ones', 'list_todos', {'include_done': True}, None),
    item(198, '2026-11-03', [U('what do I have to do'), A(TODOS, 'list_todos')],
         'move the physio to friday', 'update_todo', {'doc_id': '5gHt1ZyLm9', 'due': '2026-11-06'}, None),
    item(199, '2026-11-03', [U('what do I have to do'), A(TODOS, 'list_todos')],
         'Get rid of the dry cleaning one, not doing it', 'delete_todo', {'doc_id': 'c4Rr8NnXe0'}, None),
    item(200, '2026-11-03', [], 'what do i still have to do today', 'list_todos', {}, None),
]

write(items, 151)
