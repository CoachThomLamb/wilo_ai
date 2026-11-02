"""Round 2 (2026-10-29): today's date is in the prompt now ("Today is Tuesday, 2026-11-03."), so relative dates
("friday", "tomorrow") must become real ones. Also: yes to a drafted workout or profile change → write=True,
and a few more coaching_method openers.
Nov 2026: Sun 1, Mon 2, Tue 3, Wed 4, Thu 5, Fri 6, Sat 7, Sun 8, Mon 9 ... Mon 16, Tue 17.
"""
import copy

from lib import *
from base import *

S, SD = SHOULDERS, SHOULDERS_DOC
L, LD = LEGS, LEGS_DOC
C, CD = CHEST, CHEST_DOC
B, BD = BACK, BACK_DOC
R, RD = LOWER, LOWER_DOC
P, PD = PUMP, PUMP_DOC
M, MD = ARMS, ARMS_DOC
K = CARDIO
TODOS = 'Open: 1. Laundry [id Fg5Tn2WqZ8] 2. Meal prep Sunday (Nov 8) [id k0Mb7RxEc3] 3. Return Amazon package [id Vs4Yh9PoL1]'
TODOS2 = 'Open: 1. Physio (Nov 6) [id 5gHt1ZyLm9] 2. Buy chalk [id Qe7Wn3KdR2] 3. Call the bank [id Hj2Lp8VsT6]'


def on(w, date):
    """The same draft for another day."""
    w2 = copy.deepcopy(w)
    w2['assignedFor'] = date
    return w2


AW = lambda w, write: {'workout': w, 'write': write}

items = [
    # --- add_todo: relative dates → real dates ---
    item(351, '2026-11-03', [], 'remind me to book a physio appointment for friday', 'add_todo',
         {'text': 'Book a physio appointment', 'due': '2026-11-06'}, sc(L, LD)),
    item(352, '2026-11-05', [], 'add buy groceries tomorrow', 'add_todo', {'text': 'Buy groceries', 'due': '2026-11-06'},
         None),
    item(353, '2026-11-06', [], 'add a todo, call mom on sunday', 'add_todo', {'text': 'Call mom', 'due': '2026-11-08'},
         sc(B, BD)),
    item(354, '2026-11-09', [], 'put pick up dry cleaning on wednesday', 'add_todo',
         {'text': 'Pick up dry cleaning', 'due': '2026-11-11'}, None),
    item(355, '2026-11-12', [], 'remind me to pay the phone bill monday', 'add_todo',
         {'text': 'Pay the phone bill', 'due': '2026-11-16'}, sc(C2, C2_DOC)),
    item(356, '2026-10-30', [], 'add get a haircut saturday at 11', 'add_todo',
         {'text': 'Get a haircut', 'due': '2026-10-31 11:00'}, None),
    item(357, '2026-11-08', [], 'todo meal prep tonight at 6', 'add_todo', {'text': 'Meal prep', 'due': '2026-11-08 18:00'},
         None),
    item(358, '2026-11-02', [], 'add renew my license, needs to be done by thursday', 'add_todo',
         {'text': 'Renew my license', 'due': '2026-11-05'}, sc(S, SD)),
    item(359, '2026-11-10', [], 'Uh, add a to-do, um, to text Jake tomorrow morning', 'add_todo',
         {'text': 'Text Jake', 'due': '2026-11-11 09:00'}, sc(L2, L2_DOC)),
    item(360, '2026-11-13', [], 'add order more creatine for tuesday', 'add_todo',
         {'text': 'Order more creatine', 'due': '2026-11-17'}, sc(M, MD)),
    item(361, '2026-11-04', [], 'add deadlift practice to my todos for friday', 'add_todo',
         {'text': 'Deadlift practice', 'due': '2026-11-06'}, None),
    item(362, '2026-11-07', [], 'remind me to wash my gym bag today', 'add_todo',
         {'text': 'Wash my gym bag', 'due': '2026-11-07'}, sc(R, RD)),
    item(363, '2026-10-29', [], 'add a todo to send the BMO application tonight at 9', 'add_todo',
         {'text': 'Send the BMO application', 'due': '2026-10-29 21:00'}, None),
    item(364, '2026-10-31', [], 'Remind me monday to cancel the old gym membership', 'add_todo',
         {'text': 'Cancel the old gym membership', 'due': '2026-11-02'}, None),

    # --- update_todo: move to a relative date ---
    item(365, '2026-11-06', [U('whats on my list'), A(TODOS, 'list_todos')],
         'push laundry to tomorrow', 'update_todo', {'doc_id': 'Fg5Tn2WqZ8', 'due': '2026-11-07'}, None),
    item(366, '2026-11-04', [U('todos?'), A(TODOS2, 'list_todos')],
         'physio got moved to monday', 'update_todo', {'doc_id': '5gHt1ZyLm9', 'due': '2026-11-09'}, None),
    item(367, '2026-11-05', [U('what do I have'), A(TODOS2, 'list_todos')],
         'Call the bank tomorrow at noon', 'update_todo', {'doc_id': 'Hj2Lp8VsT6', 'due': '2026-11-06 12:00'}, None),
    item(368, '2026-11-06', [U('Whats left on my list'), A(TODOS, 'list_todos')],
         'return the amazon thing by wednesday', 'update_todo', {'doc_id': 'Vs4Yh9PoL1', 'due': '2026-11-11'}, None),

    # --- assign_workout: the draft's date, and yes → write=True ---
    item(369, '2026-11-08', [
        U('plan tomorrow'),
        A(f'Draft for tomorrow (Mon Nov 9), push pump: {summary(P)}. Save?', 'recent_completed', 'assign_workout'),
    ], 'Ya', 'assign_workout', AW(P, True), None),
    item(370, '2026-11-08', [
        U('plan tomorrow'),
        A(f'Draft for tomorrow (Mon Nov 9), push pump: {summary(P)}. Save?', 'recent_completed', 'assign_workout'),
    ], 'actually make it for tuesday', 'assign_workout', AW(on(P, '2026-11-10'), False), None),
    item(371, '2026-11-02', [
        U('make me a legs workout'),
        A(f'Legs + triceps: {summary(L)}. Is it for today?', 'recent_completed', 'assign_workout'),
    ], 'no tomorrow', 'assign_workout', AW(on(L, '2026-11-03'), False), sc(S, SD)),
    item(372, '2026-11-10', [
        U('I want an easy cardio day next'),
        A('Treadmill 25 min for tomorrow (Wed Nov 11). Save it?', 'assign_workout'),
    ], 'Yes', 'assign_workout', AW(K, True), sc(L2, L2_DOC)),
    item(373, '2026-11-11', [
        U('plan chest for thursday'),
        A(f'Chest + biceps for Thursday: {summary(C2)}. Save?', 'recent_completed', 'exercise_history', 'assign_workout'),
    ], 'Yes.', 'assign_workout', AW(C2, True), None),
    item(374, '2026-11-12', [
        U('arms tomorrow?'),
        A(f'Arms for tomorrow (Fri Nov 13): {summary(M)}. Save?', 'recent_completed', 'assign_workout'),
    ], 'put it on saturday instead', 'assign_workout', AW(on(M, '2026-11-14'), False), sc(C2, C2_DOC)),
    item(375, '2026-11-05', [
        U('can you plan back for tomorrow'),
        A(f'Back + hamstrings + triceps for Friday: {summary(B)}. Want me to save it?', 'recent_completed',
          'assign_workout'),
    ], 'Save if', 'assign_workout', AW(B, True), sc(C, CD)),
    item(376, '2026-11-06', [
        U('saturday rehab day'),
        A(f'Lower-body rehab for Saturday: {summary(R)}. Save?', 'recent_completed', 'assign_workout'),
    ], 'Ya post it', 'assign_workout', AW(R, True), sc(B, BD)),
    item(377, '2026-11-06', [
        U('saturday rehab day'),
        A(f'Lower-body rehab for Saturday: {summary(R)}. Save?', 'assign_workout'),
        U('take out the step ups'),
        A(f'Updated: {summary(edit(R, rm("Step up")))}. Shall I save it?', 'assign_workout'),
    ], 'Yes', 'assign_workout', AW(edit(R, rm('Step up')), True), sc(B, BD)),
    item(378, '2026-11-12', [
        U('arms tomorrow?'),
        A(f'Arms for tomorrow (Fri Nov 13): {summary(M)}. Save?', 'assign_workout'),
        U('25 min treadmill instead of 5'),
        A('Treadmill is 25 minutes now. Save it?', 'assign_workout'),
    ], 'yep', 'assign_workout',
         AW(edit(M, resets('Treadmill', 't1500')), True), sc(C2, C2_DOC)),
    item(379, '2026-11-01', [
        U('plan monday'),
        A(f'Monday: {summary(S)}. Save?', 'recent_completed', 'assign_workout'),
    ], 'Ya don’t ask just do it if it’s clear.', 'assign_workout', AW(S, True), None),
    item(380, '2026-11-01', [
        U('plan monday'),
        A(f'Monday: {summary(S)}. Save?', 'recent_completed', 'assign_workout'),
    ], 'wait which day is that', None, None, None),

    # --- update_profile: yes to a drafted change → write=True ---
    item(381, '2026-11-09', [
        U('I hate the leg extension machine, remember that'),
        A('Here\'s the change, preferences + "2026-11-09: Dislikes the leg extension machine." Save?', 'get_profile',
          'update_profile'),
    ], 'Ya', 'update_profile', {
        'preferences': '- 2026-10-24: Likes dead hangs (help the shoulder a lot), sled dragging, walking/treadmill.\n- 2026-10-24: Decline front raises made both shoulders feel amazing: do them a lot more.\n- 2026-11-09: Dislikes the leg extension machine.',
        'write': True}, sc(P, PD)),
    item(382, '2026-11-13', [
        U('Goal is size now not just strength'),
        A('Here\'s the change, plan + "2026-11-13: Goal: size, with strength." Save it?', 'get_profile',
          'update_profile'),
    ], 'yes', 'update_profile', {
        'plan': '- 2026-10-24: Goal: strength.\n- 2026-11-13: Goal: size, with strength. More volume on arms and chest.',
        'write': True}, sc(M, MD)),

    # --- coaching_method: reviews, check-ins, coaching loops ---
    item(383, '2026-11-08', [], 'lets review how this week went', 'coaching_method', {}, None),
    item(384, '2026-11-02', [], 'run me through a coaching check in before I start', 'coaching_method', {}, sc(S, SD)),
    item(385, '2026-11-15', [], 'can you do the full coaching loop, review last week and set up this one', 'coaching_method',
         {}, None),
    item(386, '2026-11-01', [], 'Hey Wilo, start my weekly review', 'coaching_method', {}, None),
]

if __name__ == '__main__':
    write(items, 351)
