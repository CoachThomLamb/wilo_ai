"""Admin viewer: browse every user's workouts in Firestore (#127). Read-only, local only.

    .venv/bin/python admin-viewer/serve.py        # then open http://127.0.0.1:8768/viewer.html

Reads with the service-account key in config/wilo.json (like wilo/data.py). This shows other users' private
training data: it binds 127.0.0.1 and is never deployed.

GET /api/users                 every user: uid, email, name, last sign-in
GET /api/workouts?uid=<uid>    that user's workouts from each workout collection, newest first
"""
import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from wilo import data as wilo_data  # noqa: E402

PORT = 8768
WORKOUT_COLLECTIONS = ('workouts', 'assigned', 'completed')
_db = None


def db():
    global _db
    _db = _db or wilo_data.connect()
    return _db


def users():
    # list_documents also finds users with data but no users/{uid} doc (e.g. made before sign-in wrote one).
    out = []
    for ref in db().collection('users').list_documents():
        snap = ref.get()
        d = snap.to_dict() or {}
        out.append({'uid': ref.id, 'email': d.get('email'), 'name': d.get('name'),
                    'lastSignIn': d.get('lastSignIn')})
    return sorted(out, key=lambda u: str(u['lastSignIn'] or ''), reverse=True)


def when(doc):
    """The date to sort a workout by: when it was finished, else what it's planned for, else its doc id."""
    return str(doc.get('finishedAt') or doc.get('assignedFor') or doc.get('createdAt') or '')


def workouts(uid):
    out = []
    for name in WORKOUT_COLLECTIONS:
        for snap in wilo_data.collection(db(), uid, name).stream():
            out.append({'collection': name, 'docId': snap.id, **snap.to_dict()})
    return sorted(out, key=when, reverse=True)


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        try:
            if url.path == '/api/users':
                return self._json(users())
            if url.path == '/api/workouts':
                return self._json(workouts(parse_qs(url.query)['uid'][0]))
        except Exception as e:  # show the reason on the page (bad key, no network, ...)
            return self._send(500, f'{type(e).__name__}: {e}'.encode())
        if url.path != '/viewer.html':
            return self._send(404, b'not here')
        super().do_GET()

    def _json(self, obj):
        self._send(200, json.dumps(obj, default=str, ensure_ascii=False).encode(), 'application/json')

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def _send(self, code, body, kind='text/plain; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    print(f'http://127.0.0.1:{PORT}/viewer.html  (read-only)')
    ThreadingHTTPServer(('127.0.0.1', PORT), partial(Handler, directory=str(HERE))).serve_forever()
