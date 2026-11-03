"""Tests for wilo/hevy_import.py. No Firestore: write() gets the fake db from test_wilo_data.

    .venv/bin/python -m unittest discover tests
"""

import csv
import io
import tempfile
import unittest
from zoneinfo import ZoneInfo

from test_wilo_data import FakeDB

from wilo import hevy_import as hevy

TZ = ZoneInfo('America/Toronto')
HEADER = ('title,start_time,end_time,description,exercise_title,superset_id,exercise_notes,set_index,set_type,'
          'weight_lbs,reps,distance_miles,duration_seconds,rpe')
CSV = HEADER + '''
Pull Day,"24 Sep 2026, 18:02","24 Sep 2026, 19:10",felt strong,Lat Pulldown (Cable),,seat 4,0,warmup,60,12,,,
Pull Day,"24 Sep 2026, 18:02","24 Sep 2026, 19:10",felt strong,Lat Pulldown (Cable),,seat 4,1,normal,100,10,,,8
Pull Day,"24 Sep 2026, 18:02","24 Sep 2026, 19:10",felt strong,Dead Hang,,,0,normal,,,,45,
Pull Day,"24 Sep 2026, 18:02","24 Sep 2026, 19:10",felt strong,Lat Pulldown (Cable),,,0,failure,80,8,,,
Legs,"20 Sep 2026, 09:00","20 Sep 2026, 10:00",,Walking,,,0,normal,,,1.5,,
'''


def rows(text):
    return list(csv.DictReader(io.StringIO(text)))


class HevyImportTest(unittest.TestCase):
    def setUp(self):
        self.docs = hevy.workouts(rows(CSV), TZ)

    def test_one_workout_per_hevy_session_oldest_first(self):
        self.assertEqual(list(self.docs), ['hevy-20260920-0900', 'hevy-20260924-1802'])
        pull = self.docs['hevy-20260924-1802']
        self.assertEqual((pull['name'], pull['source'], pull['note']), ('Pull Day', 'hevy', 'felt strong'))
        self.assertEqual(pull['startedAt'], '2026-09-24T22:02:00.000Z')  # Toronto is UTC-4 in September
        self.assertEqual(pull['finishedAt'], '2026-09-24T23:10:00.000Z')
        self.assertFalse(pull['inProgress'])

    def test_exercises_in_order_and_a_later_repeat_is_its_own_entry(self):
        names = [e['name'] for e in self.docs['hevy-20260924-1802']['exercises']]
        self.assertEqual(names, ['Lat Pulldown (Cable)', 'Dead Hang', 'Lat Pulldown (Cable)'])

    def test_sets_keep_load_reps_type_and_rpe(self):
        lat = self.docs['hevy-20260924-1802']['exercises'][0]
        self.assertEqual(lat['note'], 'seat 4')
        self.assertEqual(lat['custom_name'], 'Hevy')
        self.assertEqual(lat['sets'], [{'lbs': 60, 'reps': 12, 'done': True, 'custom': 'warmup'},
                                       {'lbs': 100, 'reps': 10, 'done': True, 'custom': 'RPE 8'}])

    def test_duration_only_sets_are_timed_and_distance_goes_in_custom(self):
        hang = self.docs['hevy-20260924-1802']['exercises'][1]
        self.assertTrue(hang['timed'])
        self.assertEqual(hang['sets'], [{'lbs': '', 'reps': 45, 'done': True, 'custom': None}])
        walk = self.docs['hevy-20260920-0900']['exercises'][0]
        self.assertEqual(walk['sets'][0]['custom'], '1.5 mi')

    def test_kg_exports_become_lbs(self):
        text = HEADER.replace('weight_lbs', 'weight_kg') + '\nX,"1 Oct 2026, 08:00","1 Oct 2026, 09:00",,Squat,,,0,normal,100,5,,,\n'
        s = hevy.workouts(rows(text), TZ)['hevy-20261001-0800']['exercises'][0]['sets'][0]
        self.assertEqual(s['lbs'], 220.5)

    def test_every_workout_passes_the_schema(self):
        with tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False) as f:
            f.write(CSV)
        docs, errors = hevy.load(f.name, TZ)
        self.assertEqual(errors, {})
        self.assertEqual(len(docs), 2)

    def test_write_skips_what_is_already_there(self):
        db = FakeDB({'users/u1/completed/hevy-20260920-0900': {'id': 'old'}})
        written, skipped = hevy.write(db, 'u1', self.docs)
        self.assertEqual((written, skipped), (['hevy-20260924-1802'], ['hevy-20260920-0900']))
        self.assertEqual(db.store['users/u1/completed/hevy-20260920-0900'], {'id': 'old'})  # untouched
        self.assertNotIn('users/thom/completed/hevy-20260924-1802', db.store)  # only the given uid
        self.assertEqual(hevy.write(db, 'u1', self.docs), ([], list(self.docs)))  # re-run: nothing new


if __name__ == '__main__':
    unittest.main()
