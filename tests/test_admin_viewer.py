"""Tests for admin-viewer/serve.py (#176): usage numbers, and the read-only tracker built from the real
fe/index.html. If the tracker changes shape, these fail instead of the viewer serving a page that can write.

    .venv/bin/python -m unittest discover tests
"""

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('admin_serve', ROOT / 'admin-viewer' / 'serve.py')
serve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serve)

TODAY = '2026-11-17'


def workout(status, day, planned=0, logged=0, finished=None):
    return {'status': status, 'assignedFor': day, 'finishedAt': finished,
            'exercises': [{'name': 'squat', 'sets': [{'reps': 5}] * planned}],
            'log': [{'name': 'squat', 'sets': [{'reps': 5, 'done': True}] * logged + [{'reps': 5, 'done': False}]}]}


class Usage(unittest.TestCase):
    def test_counts_and_rates(self):
        ws = [workout('done', '2026-11-10', planned=4, logged=3, finished='2026-11-10T18:00:00Z'),
              workout('done', '2026-11-12', planned=4, logged=4, finished='2026-11-12T18:00:00Z'),
              workout('planned', '2026-11-14'),            # missed: its day passed
              workout('in progress', '2026-11-15'),        # missed too: never finished
              workout('planned', '2026-11-17'),            # today: upcoming, not missed
              workout('planned', '2026-11-20')]
        u = serve.usage(ws, TODAY)
        self.assertEqual((u['workouts'], u['done'], u['missed'], u['upcoming']), (6, 2, 2, 2))
        self.assertEqual(u['completion'], 0.5)
        self.assertEqual(u['sets'], round(7 / 8, 2))
        self.assertEqual(u['lastDone'], '2026-11-12')

    def test_no_workouts(self):
        u = serve.usage([], TODAY)
        self.assertEqual((u['done'], u['completion'], u['sets'], u['lastDone']), (0, None, None, None))


class ViewerPage(unittest.TestCase):
    def setUp(self):
        self.html = serve.TRACKER.read_text()
        self.page = serve.viewer_page(self.html, 'uid-123', 'a@b.c')

    def test_firebase_is_gone(self):
        self.assertNotIn('gstatic.com/firebasejs', self.page.split('<body')[0])
        self.assertNotIn('import("./auth.js")', self.page)
        self.assertNotRegex(self.page, r'src="\./(chat|media)\.js"')

    def test_writes_are_blocked(self):
        self.assertIn("window.__setDoc = blocked('setDoc')", self.page)
        self.assertIn("window.__updateDoc = blocked('updateDoc')", self.page)
        # The tracker writes only through these two (if that changes, the viewer must too).
        body = self.page.split('</head>', 1)[1]
        self.assertEqual(set(re.findall(r'window\.__(setDoc|updateDoc|onSnapshot)\b', body)),
                         {'setDoc', 'updateDoc', 'onSnapshot'})
        self.assertNotRegex(body, r'\b(addDoc|deleteDoc|writeBatch|runTransaction)\b')

    def test_localstorage_cleared_before_the_tracker_restores_a_draft(self):
        self.assertLess(self.page.index(serve.CLEAR), self.page.index('restore();'))

    def test_user_is_escaped(self):
        page = serve.viewer_page(self.html, 'x', '</script><b>')
        self.assertIn('{"uid": "x", "email": "<\\/script><b>"}', page)
        self.assertNotIn('</script><b>', page)

    def test_tracker_changed_shape_refuses(self):
        with self.assertRaises(ValueError):
            serve.viewer_page(self.html.replace('window.__setDoc = setDoc;', ''), 'x', 'y')


if __name__ == '__main__':
    unittest.main()
