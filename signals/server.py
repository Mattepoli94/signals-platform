"""Local website with editing: python -m signals serve  ->  http://localhost:8000
Serves site/ and a small API used by the pages (save settings, add top-ups, refresh, upload)."""
from __future__ import annotations

import json
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from . import SITE
from . import config as C
from . import data as D
from . import pipeline as P

LOCK = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter console
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith('/api/ping'):
            return self._json(200, {'ok': True})
        if self.path in ('/', ''):
            self.path = '/index.html'
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        if n > 20_000_000:
            return self._json(413, {'ok': False, 'error': 'file too large'})
        try:
            body = json.loads(self.rfile.read(n) or b'{}')
        except json.JSONDecodeError:
            return self._json(400, {'ok': False, 'error': 'bad JSON'})
        try:
            with LOCK:
                if self.path == '/api/op':
                    msg = 'no change' if body.get('op') in ('import', 'none') else C.apply(body)
                    P.run('build', fetch=False, email=False)
                    return self._json(200, {'ok': True, 'message': msg})
                if self.path == '/api/refresh':
                    rep = P.run('us', fetch=True, email=False)
                    bad = [k for k, v in rep['refresh'].items() if not v['ok']]
                    return self._json(200, {'ok': True, 'message': 'Data refreshed' + (f' (failed: {", ".join(bad)})' if bad else '')})
                if self.path == '/api/upload':
                    r = D.import_csv(body['asset'], body['text'])
                    P.run('build', fetch=False, email=False)
                    return self._json(200, {'ok': True, 'message': f"{r['asset']}: {r['rows_in_file']} rows ({r['first']} to {r['last']}), {r['rows_added']} new"})
        except Exception as e:  # noqa: BLE001 - report every error to the page
            return self._json(400, {'ok': False, 'error': str(e)[:300]})
        return self._json(404, {'ok': False, 'error': 'unknown endpoint'})


def serve(port: int = 8000):
    if not (SITE / 'index.html').exists():
        P.run('build', fetch=False, email=False)
    httpd = ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=str(SITE)))
    url = f'http://localhost:{port}/'
    print(f'Signals running at {url}  (Ctrl+C to stop)')
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001
        pass
    httpd.serve_forever()
