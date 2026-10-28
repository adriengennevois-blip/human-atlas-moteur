# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

import math
from html import escape

from . import data as D
from .chart import Chart, summary_fr
from .themes import FICHE

W, H_CHART = 1180, 1060

# Couleurs : hd/themes.py (FICHE).
BG, BODY, EMPTY = FICHE["bg"], FICHE["body"], FICHE["empty"]
RED, WHITE, MUTED, TEXT = FICHE["red"], FICHE["white"], FICHE["muted"], FICHE["text"]
CENTER_COLORS = FICHE["centers"]
LABEL_ON_DEFINED = FICHE["label_on_defined"]
PERSONALITY_BAR, GATE_BADGE, GATE_BADGE_TEXT = FICHE["personality_bar"], FICHE["gate_badge"], FICHE["gate_badge_text"]

CENTER_SHAPES = {
    "head": ("poly", [(588, 64), (656, 176), (520, 176)]),
    "ajna": ("poly", [(520, 202), (656, 202), (588, 308)]),
    "throat": ("rect", (532, 350, 112, 120)),
    "g": ("poly", [(588, 502), (661, 575), (588, 648), (515, 575)]),
    "heart": ("poly", [(730, 604), (774, 694), (670, 672)]),
    "sacral": ("rect", (532, 730, 112, 116)),
    "root": ("rect", (532, 884, 112, 116)),
    "spleen": ("poly", [(312, 704), (418, 778), (312, 850)]),
    "solar_plexus": ("poly", [(864, 704), (864, 850), (758, 778)]),
}

GATE_POS = {
    64: (562, 162), 61: (588, 162), 63: (614, 162),
    47: (562, 216), 24: (588, 216), 4: (614, 216), 17: (566, 262), 11: (610, 262), 43: (588, 292),
    62: (562, 364), 23: (588, 364), 56: (614, 364), 16: (546, 388), 20: (546, 418),
    35: (630, 386), 12: (630, 410), 45: (630, 434), 31: (562, 456), 8: (588, 456), 33: (614, 456),
    1: (588, 520), 7: (562, 540), 13: (614, 540), 10: (532, 575), 25: (644, 575),
    15: (562, 610), 46: (614, 610), 2: (588, 630),
    21: (730, 624), 51: (714, 642), 26: (688, 670), 40: (758, 684),
    5: (562, 744), 14: (588, 744), 29: (614, 744), 34: (546, 770), 27: (546, 810), 59: (630, 810),
    42: (562, 832), 3: (588, 832), 9: (614, 832),
    53: (562, 898), 60: (588, 898), 52: (614, 898), 54: (546, 922), 38: (546, 950), 58: (546, 978),
    19: (630, 922), 39: (630, 950), 41: (630, 978),
    48: (326, 722), 57: (350, 738), 44: (376, 756), 50: (402, 778), 32: (376, 800), 28: (350, 818),
    18: (326, 834),
    36: (850, 722), 22: (826, 738), 37: (800, 756), 6: (774, 778), 49: (800, 800), 55: (826, 818),
    30: (850, 834),
}

# Control points for curved channels; straight otherwise.
CHANNEL_CURVES = {
    (16, 48): ((430, 410), (330, 560)),
    (20, 57): ((450, 440), (360, 610)),
    (10, 20): ((500, 540), (510, 450)),
    (10, 34): ((490, 640), (500, 745)),
    (10, 57): ((440, 600), (360, 650)),
    (20, 34): ((470, 480), (445, 700)),
    (34, 57): ((470, 772), (420, 748)),
    (35, 36): ((750, 410), (846, 560)),
    (12, 22): ((730, 440), (820, 610)),
    (21, 45): ((690, 470), (730, 560)),
    (26, 44): ((560, 660), (440, 690)),
    (32, 54): ((410, 880), (480, 915)),
    (28, 38): ((390, 910), (470, 950)),
    (18, 58): ((360, 940), (450, 980)),
    (19, 49): ((770, 880), (700, 915)),
    (39, 55): ((790, 910), (710, 950)),
    (30, 41): ((820, 940), (730, 980)),
    (6, 59): ((720, 790), (680, 805)),
    (27, 50): ((490, 802), (450, 790)),
    (25, 51): ((680, 600), (700, 625)),
    (37, 40): ((780, 710), (790, 740)),
}


def _path(a, b):
    """Return (svg path d, length in px)."""
    (x1, y1), (x2, y2) = GATE_POS[a], GATE_POS[b]
    ctrl = CHANNEL_CURVES.get((a, b))
    if not ctrl:
        return f"M{x1},{y1} L{x2},{y2}", math.hypot(x2 - x1, y2 - y1)
    (c1x, c1y), (c2x, c2y) = ctrl
    pts = []
    for i in range(201):
        t = i / 200
        u = 1 - t
        pts.append((u**3 * x1 + 3 * u * u * t * c1x + 3 * u * t * t * c2x + t**3 * x2,
                    u**3 * y1 + 3 * u * u * t * c1y + 3 * u * t * t * c2y + t**3 * y2))
    length = sum(math.dist(pts[i], pts[i + 1]) for i in range(200))
    return f"M{x1},{y1} C{c1x},{c1y} {c2x},{c2y} {x2},{y2}", length


def _dash(start, end, stripe=None):
    if stripe is None:
        return f"0 {start:.1f} {end - start:.1f} 4000"
    parts, pos = [0, start], start
    while pos + stripe <= end:
        parts += [stripe, stripe]
        pos += 2 * stripe
    parts[-1] += 4000
    return " ".join(f"{p:.1f}" for p in parts)


def _half(d, length, sides, first):
    mid = length / 2
    s, e = (0, mid) if first else (mid, length)
    out = []
    if "design" in sides:
        out.append(f'<path d="{d}" stroke="{RED}" stroke-width="11" '
                   f'fill="none" stroke-dasharray="{_dash(s, e)}"/>')
    if "personality" in sides:
        dash = _dash(s, e, 4.5 if "design" in sides else None)
        out.append(f'<path d="{d}" stroke="{WHITE}" stroke-width="11" '
                   f'fill="none" stroke-dasharray="{dash}"/>')
    return out


def _center_shape(kind, geom, fill):
    if kind == "rect":
        x, y, w, h = geom
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}"/>'
    pts = " ".join(f"{x},{y}" for x, y in geom)
    return (f'<polygon points="{pts}" fill="{fill}" stroke="{fill}" '
            f'stroke-width="18" stroke-linejoin="round"/>')


def _arrow(x, y, direction, color):
    dx = -1 if direction == "gauche" else 1
    return (f'<path d="M{x - 11 * dx},{y} H{x + 11 * dx} M{x + 3 * dx},{y - 8} L{x + 11 * dx},{y} '
            f'L{x + 3 * dx},{y + 8}" stroke="{color}" stroke-width="2.6" fill="none" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def _planet_column(acts, side):
    color = RED if side == "design" else TEXT
    x_title = 128 if side == "design" else 1058
    out = [
        f'<text x="{x_title}" y="90" fill="{TEXT}" font-size="21" text-anchor="middle">'
        f'{"Design" if side == "design" else "Personnalité"}</text>',
        f'<rect x="{x_title - 76}" y="102" width="152" height="3" fill="{RED if side == "design" else PERSONALITY_BAR}"/>',
    ]
    for i, p in enumerate(D.PLANETS):
        a = acts[p]
        y = 150 + i * 68
        glyph = D.PLANET_GLYPHS[p] + "︎"
        sub = f"c{a.color} t{a.tone} b{a.base}"
        if side == "design":
            out.append(f'<text x="60" y="{y}" fill="{color}" font-size="26" text-anchor="middle">{glyph}</text>')
            out.append(f'<text x="92" y="{y}" fill="{color}" font-size="24">{a.label}</text>')
            out.append(f'<text x="94" y="{y + 20}" fill="{MUTED}" font-size="12">{sub}</text>')
        else:
            out.append(f'<text x="1120" y="{y}" fill="{color}" font-size="26" text-anchor="middle">{glyph}</text>')
            out.append(f'<text x="1088" y="{y}" fill="{color}" font-size="24" text-anchor="end">{a.label}</text>')
            out.append(f'<text x="1086" y="{y + 20}" fill="{MUTED}" font-size="12" text-anchor="end">{sub}</text>')
    return out


def render_svg(c: Chart) -> str:
    info = summary_fr(c)
    header = [c.name] if c.name else []
    m = c.meta
    if m.get("local"):
        header.append(f"Naissance : {m['local']} ({m.get('tz', '')}, UTC{m.get('offset', '')})")
    if m.get("place"):
        header.append(f"Lieu : {m['place']}")
    header.append(f"Naissance UTC : {c.birth_utc:%d/%m/%Y %H:%M:%S}  ·  "
                  f"Design UTC : {c.design_utc:%d/%m/%Y %H:%M:%S}")
    channels_txt = ", ".join(f"{a}-{b}" for a, b in c.channels) or "aucun"
    defined_txt = ", ".join(D.CENTER_NAMES_FR[x] for x in c.defined_centers) or "aucun"
    lines = header + [""] + info + [f"Canaux : {channels_txt}", f"Centres définis : {defined_txt}"]
    height = H_CHART + 40 + 34 * len(lines)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" height="{height}" '
         f'font-family="Inter, Helvetica, Arial, sans-serif">',
         f'<rect width="{W}" height="{height}" fill="{BG}"/>',
         f'<ellipse cx="588" cy="215" rx="112" ry="140" fill="{BODY}"/>',
         f'<rect x="536" y="300" width="104" height="100" fill="{BODY}"/>',
         f'<path d="M470,392 Q400,396 382,450 L250,800 Q232,900 250,1030 L926,1030 Q944,900 926,800 '
         f'L794,450 Q776,396 706,392 Z" fill="{BODY}"/>']

    paths = {ch: _path(*ch) for ch in D.CHANNELS}
    for d, _ in paths.values():
        o.append(f'<path d="{d}" stroke="{EMPTY}" stroke-width="20" fill="none"/>')
    for (a, b), (d, length) in paths.items():
        if a in c.active_gates:
            o += _half(d, length, c.active_gates[a], True)
        if b in c.active_gates:
            o += _half(d, length, c.active_gates[b], False)

    for name, (kind, geom) in CENTER_SHAPES.items():
        fill = CENTER_COLORS[name] if name in c.defined_centers else EMPTY
        o.append(_center_shape(kind, geom, fill))

    for gate, (x, y) in GATE_POS.items():
        if gate in c.active_gates:
            o.append(f'<circle cx="{x}" cy="{y}" r="11.5" fill="{GATE_BADGE}"/>')
            o.append(f'<text x="{x}" y="{y + 4.5}" fill="{GATE_BADGE_TEXT}" font-size="12.5" font-weight="700" '
                     f'text-anchor="middle">{gate}</text>')
        else:
            center = D.GATE_CENTER[gate]
            color = LABEL_ON_DEFINED.get(center, MUTED) if center in c.defined_centers else MUTED
            o.append(f'<text x="{x}" y="{y + 4.5}" fill="{color}" font-size="12.5" '
                     f'text-anchor="middle">{gate}</text>')

    o += _planet_column(c.design, "design")
    o += _planet_column(c.personality, "personality")
    v = c.variables
    o.append(_arrow(262, 184, v["design_sun"], RED))
    o.append(_arrow(262, 320, v["design_node"], RED))
    o.append(_arrow(918, 184, v["personality_sun"], WHITE))
    o.append(_arrow(918, 320, v["personality_node"], WHITE))

    y = H_CHART + 50
    for i, line in enumerate(lines):
        weight = ' font-weight="700"' if i == 0 and c.name else ""
        size = 26 if i == 0 and c.name else 19
        o.append(f'<text x="60" y="{y}" fill="{TEXT}" font-size="{size}"{weight}>{escape(line)}</text>')
        y += 34
    o.append("</svg>")
    return "\n".join(o)
