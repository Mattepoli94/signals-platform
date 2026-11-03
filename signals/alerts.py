"""Email alerts. SMTP settings come from environment variables (GitHub secrets):
SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD, ALERT_TO, ALERT_FROM (optional).
Without them, emails are written to state/outbox/ so you can preview them."""
from __future__ import annotations

import json
import os
import smtplib
import ssl
from email.message import EmailMessage

from . import STATE

LOG = STATE / 'alerts_log.json'


def _log() -> dict:
    return json.loads(LOG.read_text()) if LOG.exists() else {}


def already_sent(alert_id: str) -> bool:
    return alert_id in _log()


def mark_sent(ids, when: str):
    log = _log()
    for i in ids:
        log[i] = when
    # keep the log small
    LOG.write_text(json.dumps(dict(sorted(log.items(), key=lambda kv: kv[1])[-2000:]), indent=0))


def configured() -> bool:
    return all(os.environ.get(k) for k in ('SMTP_HOST', 'SMTP_USER', 'SMTP_PASSWORD', 'ALERT_TO'))


def send(subject: str, html: str, text: str) -> str:
    if not configured():
        out = STATE / 'outbox'
        out.mkdir(parents=True, exist_ok=True)
        safe = ''.join(ch if ch.isalnum() else '_' for ch in subject)[:80]
        (out / f'{safe}.html').write_text(html)
        return 'saved to state/outbox (email not configured)'
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = os.environ.get('ALERT_FROM') or os.environ['SMTP_USER']
    msg['To'] = os.environ['ALERT_TO']
    msg.set_content(text)
    msg.add_alternative(html, subtype='html')
    port = int(os.environ.get('SMTP_PORT') or 587)
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(os.environ['SMTP_HOST'], port, context=ctx, timeout=30) as s:
            s.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
            s.send_message(msg)
    else:
        with smtplib.SMTP(os.environ['SMTP_HOST'], port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
            s.send_message(msg)
    return 'sent'
