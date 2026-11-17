"""Admin viewer: browse every user's workouts in Firestore (#127). Read-only, local only.

    .venv/bin/python admin-viewer/serve.py        # then open http://127.0.0.1:8768/viewer.html

Reads with the service-account key in config/wilo.json (like wilo/data.py). This shows other users' private
training data: it binds 127.0.0.1 and is never deployed.

GET /api/users                 every user: uid, email, name, last sign-in, usage numbers (#176)
GET /api/workouts?uid=<uid>    that user's workouts from each workout collection, newest first
GET /view?uid=<uid>            that user's real tracker (fe/index.html), read-only (#176)
"""
import json
import re
import sys
from datetime import date, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from wilo import data as wilo_data  # noqa: E402

PORT = 8768
WORKOUT_COLLECTIONS = ('workouts',)   # assigned and completed stay as the pre-#126 backup
TRACKER = HERE.parent / 'fe' / 'index.html'
UID = re.compile(r'^[A-Za-z0-9_-]{1,128}$')
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
                    'createdAt': d.get('createdAt'), 'lastSignIn': d.get('lastSignIn'),
                    'usage': usage(workouts(ref.id), date.today().isoformat())})
    return sorted(out, key=lambda u: str(u['lastSignIn'] or ''), reverse=True)


def usage(ws, today):
    """How a user trains (#176). Plan completion = done ÷ (done + missed), where missed = not done and its day has
    passed. Sets = sets logged done ÷ sets planned, over done workouts. None when there's nothing to divide."""
    day = lambda w: str(w.get('assignedFor') or w.get('finishedAt') or '')[:10]
    done = [w for w in ws if w.get('status') == 'done']
    missed = [w for w in ws if w.get('status') != 'done' and day(w) and day(w) < today]
    planned_sets = sum(len(x.get('sets') or []) for w in done for x in w.get('exercises') or [])
    logged_sets = sum(1 for w in done for x in w.get('log') or [] for s in x.get('sets') or [] if s.get('done'))
    return {
        'workouts': len(ws), 'done': len(done), 'missed': len(missed),
        'upcoming': sum(1 for w in ws if w.get('status') != 'done' and day(w) >= today),
        'completion': round(len(done) / (len(done) + len(missed)), 2) if done or missed else None,
        'sets': round(logged_sets / planned_sets, 2) if planned_sets else None,
        'lastDone': max((str(w.get('finishedAt') or '')[:10] for w in done), default=None),
    }


# The tracker's own Firebase setup: the first module script in its <head>. viewer_page swaps it.
SETUP = re.compile(r'<script type="module">(?:(?!</script>).)*?window\.__setDoc = setDoc;.*?</script>', re.S)
BACKEND = re.compile(r'<script type="module" src="\./(chat|media)\.js"></script>\n?')

# Runs before the tracker's own script, which restores a draft from localStorage: one user's draft must never
# show on another's view.
CLEAR = '<script>try { localStorage.clear(); } catch (e) {}</script>'

# Stands in for Firebase: the workouts listener polls this server, writes do nothing, the user is "signed in".
SHIM = '''<script type="module">
  // Admin viewer (#176), injected by admin-viewer/serve.py. Read-only: nothing here writes to Firestore.
  const USER = %s;
  const blocked = what => async () => console.warn('[viewer] write blocked:', what);
  window.__setDoc = blocked('setDoc');
  window.__updateDoc = blocked('updateDoc');
  window.__onSnapshot = (ref, next, error) => {
    let stop = false, last = '';
    async function pull() {
      try {
        const r = await fetch('/api/workouts?uid=' + encodeURIComponent(USER.uid));
        const text = await r.text();
        if (!r.ok) throw new Error(text);
        if (text !== last) {
          last = text;
          next({ docs: JSON.parse(text).map(w => ({ id: w.docId, data: () => w })) });
        }
      } catch (e) { if (error) error(e); }
      if (!stop) setTimeout(pull, 15000);
    }
    pull();
    return () => { stop = true; };
  };
  const nop = async () => {};
  window.__auth = { signIn: nop, signOut: nop, onUser: cb => cb(USER), currentUser: () => USER,
                    userCol: name => ({ name }), userDoc: (name, id) => ({ name, id }) };
  document.body.insertAdjacentHTML('afterbegin', '<div style="position:fixed;top:4px;right:4px;z-index:9999;' +
    'pointer-events:none;background:#dc2626;color:#fff;font:600 11px system-ui;padding:2px 8px;border-radius:4px">' +
    'VIEWING ' + USER.email.replace(/[<>&]/g, '') + ' · READ-ONLY</div>');
  window.dispatchEvent(new CustomEvent('wilo-user', { detail: USER }));
</script>'''


def viewer_page(html, uid, email):
    """The tracker's HTML with Firebase swapped for SHIM, chat/media (they call the backend) removed and
    localStorage cleared first. Raises if the tracker changed shape, rather than serve a page that could write."""
    if len(SETUP.findall(html)) != 1:
        raise ValueError("fe/index.html changed: can't find its Firebase setup script, so no read-only view")
    user = json.dumps({'uid': uid, 'email': email or uid}).replace('</', '<\\/')
    html = SETUP.sub(lambda _: SHIM % user, html)
    html = BACKEND.sub('', html)
    return html.replace('<head>', '<head>\n' + CLEAR, 1)


def to_json(value):
    return value.isoformat() if isinstance(value, (date, datetime)) else str(value)


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
            if url.path == '/view':
                uid = parse_qs(url.query).get('uid', [''])[0]
                if not UID.match(uid):
                    return self._send(400, b'bad uid')
                email = (db().collection('users').document(uid).get().to_dict() or {}).get('email')
                page = viewer_page(TRACKER.read_text(), uid, email)
                return self._send(200, page.encode(), 'text/html; charset=utf-8')
        except Exception as e:  # show the reason on the page (bad key, no network, ...)
            return self._send(500, f'{type(e).__name__}: {e}'.encode())
        if url.path != '/viewer.html':
            return self._send(404, b'not here')
        super().do_GET()

    def _json(self, obj):
        self._send(200, json.dumps(obj, default=to_json, ensure_ascii=False).encode(), 'application/json')

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
