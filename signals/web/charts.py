"""Small server-side SVG line charts (no JavaScript, prints and emails well)."""
from __future__ import annotations

import math
from datetime import date
from html import escape


def _nice(lo, hi, n=5):
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=raw)
    start = math.floor(lo / step) * step
    ticks, v = [], start
    while v <= hi + step * 0.5:
        ticks.append(v)
        v += step
    return ticks


def line_chart(series: list, width=1100, height=320, yfmt='£{:,.0f}', label='chart', zones=None) -> str:
    """series: [{'name', 'color', 'dash': bool, 'width': float, 'points': [(iso_date, value), ...]}]
    zones: optional list of booleans aligned with the first series' points (shaded bands)."""
    pts_all = [(d, v) for s in series for d, v in s['points'] if v is not None]
    if len(pts_all) < 2:
        return '<p class="muted small">Not enough history to draw a chart yet.</p>'
    dates = sorted({d for d, _ in pts_all})
    d0, d1 = date.fromisoformat(dates[0]), date.fromisoformat(dates[-1])
    span = max((d1 - d0).days, 1)
    vals = [v for _, v in pts_all]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.06 or abs(hi) * 0.05 or 1
    ticks = _nice(lo - pad, hi + pad)
    lo, hi = ticks[0], ticks[-1]
    L, R, T, B = 76, width - 16, 16, height - 34

    def X(d):
        return L + (R - L) * (date.fromisoformat(d) - d0).days / span

    def Y(v):
        return B - (B - T) * (v - lo) / (hi - lo)

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="{escape(label)}" '
           f'style="display:block;min-width:560px" xmlns="http://www.w3.org/2000/svg">']
    if zones:
        pts = series[0]['points']
        i = 0
        while i < len(pts):
            if zones[i]:
                j = i
                while j + 1 < len(pts) and zones[j + 1]:
                    j += 1
                x0, x1 = X(pts[i][0]), X(pts[j][0])
                out.append(f'<rect x="{x0 - 1:.1f}" y="{T}" width="{max(x1 - x0, 2) + 2:.1f}" height="{B - T}" fill="#E3F4EA"/>')
                i = j + 1
            else:
                i += 1
    for v in ticks:
        y = Y(v)
        out.append(f'<line x1="{L}" x2="{R}" y1="{y:.1f}" y2="{y:.1f}" stroke="#E4E8EF"/>')
        out.append(f'<text x="{L - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="12" fill="#475467" font-family="IBM Plex Mono, monospace">{escape(yfmt.format(v))}</text>')
    # x labels: ~6 evenly spaced month starts
    months = []
    y_, m_ = d0.year, d0.month
    while date(y_, m_, 1) <= d1:
        if date(y_, m_, 1) >= d0:
            months.append(date(y_, m_, 1))
        m_ += 1
        if m_ > 12:
            y_, m_ = y_ + 1, 1
    if not months:
        months = [d0]
    step = max(1, math.ceil(len(months) / 7))
    for m in months[::step]:
        x = X(m.isoformat())
        fmt = m.strftime('%b %y') if span > 200 else m.strftime('%d %b')
        out.append(f'<text x="{x:.1f}" y="{height - 10}" text-anchor="middle" font-size="12" fill="#475467" font-family="Inter, sans-serif">{fmt}</text>')
    for s in series:
        p = [(d, v) for d, v in s['points'] if v is not None]
        if len(p) < 2:
            continue
        path = ' '.join(f'{X(d):.1f},{Y(v):.1f}' for d, v in p)
        dash = ' stroke-dasharray="6 5"' if s.get('dash') else ''
        out.append(f'<polyline points="{path}" fill="none" stroke="{s["color"]}" stroke-width="{s.get("width", 2.5)}" stroke-linejoin="round"{dash}/>')
    for s in series:
        for m in s.get('markers', []):
            out.append(f'<circle cx="{X(m[0]):.1f}" cy="{Y(m[1]):.1f}" r="5" fill="{m[2] if len(m) > 2 else s["color"]}" stroke="#fff" stroke-width="2"/>')
    out.append('</svg>')
    return ''.join(out)
