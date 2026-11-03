"""Command line.

  python -m signals run --mode close|preclose|btc|build [--no-fetch] [--no-email] [--force]
  python -m signals op '{"op": "add_topup", "pot": "qqq_value", "amount": 500, "date": "2026-12-01"}'
  python -m signals import QQQ path/to/file.csv
  python -m signals serve [--port 8000]
"""
import argparse
import json
import sys

from . import config as C
from . import data as D
from . import pipeline as P


def main(argv=None):
    ap = argparse.ArgumentParser(prog='signals')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--mode', default='us', choices=['preclose', 'close', 'us', 'btc', 'build'])
    r.add_argument('--no-fetch', action='store_true')
    r.add_argument('--no-email', action='store_true')
    r.add_argument('--force', action='store_true', help='preclose: run even outside the pre-close window')
    o = sub.add_parser('op')
    o.add_argument('json')
    i = sub.add_parser('import')
    i.add_argument('asset')
    i.add_argument('file')
    s = sub.add_parser('serve')
    s.add_argument('--port', type=int, default=8000)
    a = ap.parse_args(argv)

    if a.cmd == 'run':
        from datetime import datetime, timezone
        from . import STATE
        rep = P.run(a.mode, fetch=not a.no_fetch, email=not a.no_email, force=a.force)
        print(json.dumps(rep, indent=1, default=str))
        STATE.mkdir(parents=True, exist_ok=True)
        summary = {'mode': a.mode, 'finished_utc': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'),
                   'skipped': rep.get('skipped'), 'alerts': rep.get('alerts'),
                   'refresh': {k: (v['last'] if v['ok'] else 'FAILED: ' + v['error'][:120]) for k, v in (rep.get('refresh') or {}).items()}}
        (STATE / 'last_run.json').write_text(json.dumps(summary, indent=1, default=str))
        failed = [k for k, v in (rep.get('refresh') or {}).items() if not v['ok']]
        if failed:
            print('WARNING: download failed for ' + ', '.join(failed), file=sys.stderr)
    elif a.cmd == 'op':
        op = json.loads(a.json)
        if op.get('op') in ('import', 'refresh', 'none'):
            print('no settings change')
        else:
            print(C.apply(op))
    elif a.cmd == 'import':
        print(D.import_csv(a.asset, open(a.file).read()))
    elif a.cmd == 'serve':
        from .server import serve
        serve(a.port)


if __name__ == '__main__':
    main()
