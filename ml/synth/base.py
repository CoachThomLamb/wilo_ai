"""Base workouts the synthetic chats edit. Names and cues in Thom's style (from his real workouts)."""
from lib import ex, workout, doc_id

TREAD5 = lambda: ex('Treadmill', 't300', '5 min easy walk. Good for the quad.')

SHOULDERS = workout('shoulders-bi-rehab-nov-2', '2026-11-02', [
    TREAD5(),
    ex('Massage', 't600'),
    ex('Dead hang', '2x45t', '~45s each. Opens the shoulder.'),
    ex('Serratus shrug', '3x10', "Protract and push, don't row."),
    ex('Scapular pull-up', '2x5', 'Down and back, elbows straight, slow.'),
    ex('Hammer seated shoulder press', '2x12@15 RL', 'Drop back to 10 if it pinches.'),
    ex('Lateral raise', '3x12@5'),
    ex('Sword raise', '3x6@5 RL', 'Thumb leading, light.'),
    ex('Barbell curl', '3x10@45', '45, aim for 10 clean each set.'),
], wid='prog_1793541120334')
SHOULDERS_DOC = doc_id('shoul', '2026-11-01', '18:12')

LEGS = workout('legs-tri-nov-3', '2026-11-03', [
    TREAD5(),
    ex('Leg press', '3x10@200', 'Same 200. All 10s done last time.'),
    ex('Crane-plane', '4x6'),
    ex('Hack squat', '3x8@90'),
    ex('B-stance lunge lockout', '3x8 RL'),
    ex('Tricep pushdown', '3x12@40'),
    ex('Skull crusher pushups', '3x10'),
])
LEGS_DOC = doc_id('legs-', '2026-11-01', '18:13')

CHEST = workout('chest-bi-nov-5', '2026-11-05', [
    ex('Dead hang', '2x45t', '~45s each. Opens the shoulder.'),
    ex('Serratus shrug', '3x10', "Protract and push, don't row."),
    ex('Decline front raise', '3x6@5', '6 max. Hard but shoulder-feel-good.'),
    ex('Hammer machine press', '3x10@90', 'Partial range, pain-free.'),
    ex('Pec deck', '3x12@100'),
    ex('Barbell curl', '3x10@45'),
    ex('Free motion dual cable curl', '3x15@17'),
    ex('Treadmill', 't1200', '20 min easy walk.'),
])
CHEST_DOC = doc_id('chest', '2026-11-01', '18:15')

BACK = workout('back-ham-tri-nov-6', '2026-11-06', [
    TREAD5(),
    ex('Double leg curls', '3x10@115', 'Stop if the right hamstring twinges.'),
    ex('Dumbbell RDL', '3x10@50'),
    ex('Meadows row', '3x10@70'),
    ex('Hammer machine pulldown', '3x10@120'),
    ex('Double cable row', '3x12@60'),
    ex('Dip machine', '3x12@140'),
])
BACK_DOC = doc_id('back-', '2026-11-01', '18:16')


def sc(w, d):
    """The screen tuple for a workout and its doc id."""
    return (w['name'], d)


LOWER = workout('lower-body-rehab-nov-7', '2026-11-07', [
    ex('Dragging', '6x1@135', 'Drag 6, pull 2. Heavy and slow.'),
    ex('Crane-plane', '3x10'),
    ex('Lunge stretch', '3x8'),
    ex('Single leg curls seated', '4x10@50 RL', 'Stop if the right hamstring twinges.'),
    ex('Leg extension', '3x15@70'),
    ex('Step up', '3x10'),
    ex('Bulgarian static holds', '3x3', '5 second hold, max depth.'),
    ex('Treadmill', 't900', '15 min easy walk.'),
])
LOWER_DOC = doc_id('lower', '2026-11-06', '21:40')

PUMP = workout('push-pump-nov-9', '2026-11-09', [
    ex('Dead hang', '2x45t', '~45s each. Opens the shoulder.'),
    ex('Hammer machine press', '4x10@90', 'Partial range, pain-free.'),
    ex('Incline dumbbell press', '3x10@40'),
    ex('Cable fly', '3x12@30'),
    ex('Dip machine', '3x12@140'),
    ex('Tricep pushdown', '3x12@40'),
    ex('Pushups', '2x15'),
])
PUMP_DOC = doc_id('push-', '2026-11-08', '20:05')


def again(w, name, date, made, hhmm):
    """The same workout planned for another day: (workout, doc id)."""
    import copy
    w2 = copy.deepcopy(w)
    w2.update(id=name, name=name, assignedFor=date)
    return w2, doc_id(name, made, hhmm)


S2, S2_DOC = again(SHOULDERS, 'shoulders-bi-rehab-nov-9', '2026-11-09', '2026-11-08', '19:31')
L2, L2_DOC = again(LEGS, 'legs-tri-nov-10', '2026-11-10', '2026-11-08', '19:33')
C2, C2_DOC = again(CHEST, 'chest-bi-nov-12', '2026-11-12', '2026-11-08', '19:36')

ARMS = workout('arms-pump-nov-13', '2026-11-13', [
    TREAD5(),
    ex('Barbell curl', '3x10@50'),
    ex('Hammer curl', '3x10@25'),
    ex('Preacher curl', '3x12@30'),
    ex('Tricep pushdown', '3x12@45'),
    ex('Overhead cable extension', '3x12@30'),
    ex('Dip machine', '3x12@140'),
])
ARMS_DOC = doc_id('arms-', '2026-11-12', '22:02')

CARDIO = workout('Cardio', '2026-11-11', [ex('Treadmill', 't1500', '25 min.')])
CARDIO_DOC = doc_id('Cardi', '2026-11-08', '19:34')
