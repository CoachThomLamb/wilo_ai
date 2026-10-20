"""Serve the coaching-evals viewer and save notes to notes.json in this folder.

    python3 coaching-evals/serve.py        # then open http://127.0.0.1:8765/viewer.html

GET serves files from this folder. PUT /notes.json writes the notes (pretty, sorted keys,
so git diffs stay readable). Local only: binds 127.0.0.1.
"""
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES = HERE / 'notes.json'
PORT = 8765


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/notes.json' and not NOTES.exists():
            self._send(200, b'{}')
            return
        super().do_GET()

    def do_PUT(self):
        if self.path != '/notes.json':
            self._send(404, b'only /notes.json can be written')
            return
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        try:
            notes = json.loads(body)
        except ValueError:
            self._send(400, b'not JSON')
            return
        NOTES.write_text(json.dumps(notes, indent=2, sort_keys=True, ensure_ascii=False) + '\n')
        self._send(200, b'saved')

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def _send(self, code, body):
        self.send_response(code)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    print(f'http://127.0.0.1:{PORT}/viewer.html  (notes -> {NOTES})')
    ThreadingHTTPServer(('127.0.0.1', PORT), partial(Handler, directory=str(HERE))).serve_forever()
