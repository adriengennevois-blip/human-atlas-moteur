# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""
Bodygraph Human Atlas — rendu SVG.

Principe : le dessin ne calcule rien.
  1. GABARIT : la géométrie (9 centres, 64 portes, 36 canaux) est fixe, définie
     une fois ici. validate_template() vérifie qu'elle couvre exactement les
     tables du moteur (data.CENTERS, data.CHANNELS) et que chaque porte est
     bien dessinée à l'intérieur de son centre.
  2. DONNÉES : le thème (portes actives côté Design / Personnalité) vient du
     moteur. Canaux et centres définis sont déduits des mêmes tables que lui.
  3. HABILLAGE : un « skin » ne change que les couleurs et l'ambiance.
     Les codes Human Design sont communs à tous les skins :
       rouge = Design (inconscient) · noir = Personnalité (conscient)
       rayé rouge/noir = les deux · centre coloré = défini · blanc = ouvert

Usage :
    from hd.bodygraph import render_bodygraph
    svg = render_bodygraph(chart, skin="atlas")      # chart = hd.chart.build_chart(...)
"""

from __future__ import annotations

import functools
import math
import re
import secrets
from html import escape

from . import data as D
from .themes import MIN_CONTRAST, THEMES, Gradient, Marble, contrast, solid, text_on

# --------------------------------------------------------------------------- gabarit

# Géométrie relevée sur un bodygraph standard (mybodygraph), en pixels de la
# capture de référence, puis mise à l'échelle par _S(). Les canaux partent du
# centre des numéros de porte et passent sous les centres, comme sur l'original.
#
# Circuit d'intégration (portes 10, 20, 34, 57) : comme sur les bodygraphs
# standard, ses six canaux ne sont pas six lignes séparées. Chaque porte a son
# tronçon, et les tronçons se rejoignent en un point J à gauche du G. Le canal
# 10-34 = tronçon de 10 + tronçon de 34, etc. Chaque moitié de canal garde donc
# la couleur de sa propre porte.

_SCALE = 0.62


def _S(x, y):
    return (round((x - 389) * _SCALE + 200, 2), round((y - 40) * _SCALE + 20, 2))


def _Sall(pts):
    return [_S(*p) for p in pts]


CENTER_SHAPES = {
    "head":         _Sall([(389, 24), (474, 158), (304, 158)]),
    "ajna":         _Sall([(303, 188), (473, 188), (388, 323)]),
    "throat":       _Sall([(328, 346), (448, 346), (448, 475), (328, 475)]),
    "g":            _Sall([(388, 500), (473, 585), (388, 670), (303, 585)]),
    "heart":        _Sall([(541.7, 609.5), (591.3, 717.5), (466.5, 691)]),
    "sacral":       _Sall([(328, 752), (448, 752), (448, 874), (328, 874)]),
    "root":         _Sall([(328, 916), (448, 916), (448, 1037), (328, 1037)]),
    "spleen":       _Sall([(91, 716.5), (227, 803), (91, 888)]),
    "solar_plexus": _Sall([(687, 716.5), (551, 803), (687, 888)]),
}
# Rayon des coins arrondis, mesuré sur la référence (px de référence) :
# triangles ≈ 18, carrés ≈ 20, losange du G ≈ 26.
CORNER_RADIUS = {"throat": 20, "sacral": 20, "root": 20, "g": 26, "heart": 15}
CORNER_RADIUS_DEFAULT = 18


def _rounded_corners(center):
    """Pour chaque sommet : (début de l'arc, fin de l'arc, centre, rayon, sens), à l'échelle."""
    pts = CENTER_SHAPES[center]
    r = CORNER_RADIUS.get(center, CORNER_RADIUS_DEFAULT) * _SCALE
    out = []
    n = len(pts)
    for i in range(n):
        prev, cur, nxt = pts[i - 1], pts[i], pts[(i + 1) % n]
        u1 = (prev[0] - cur[0], prev[1] - cur[1]); l1 = math.hypot(*u1); u1 = (u1[0] / l1, u1[1] / l1)
        u2 = (nxt[0] - cur[0], nxt[1] - cur[1]); l2 = math.hypot(*u2); u2 = (u2[0] / l2, u2[1] / l2)
        theta = math.acos(max(-1, min(1, u1[0] * u2[0] + u1[1] * u2[1])))
        t = r / math.tan(theta / 2)
        a = (cur[0] + u1[0] * t, cur[1] + u1[1] * t)
        b = (cur[0] + u2[0] * t, cur[1] + u2[1] * t)
        bis = (u1[0] + u2[0], u1[1] + u2[1]); lb = math.hypot(*bis); bis = (bis[0] / lb, bis[1] / lb)
        c = (cur[0] + bis[0] * r / math.sin(theta / 2), cur[1] + bis[1] * r / math.sin(theta / 2))
        turn = (cur[0] - prev[0]) * (nxt[1] - cur[1]) - (cur[1] - prev[1]) * (nxt[0] - cur[0])
        out.append((a, b, c, r, 1 if turn > 0 else 0))
    return out


def center_outline(center, per_arc=10):
    """Contour réel du centre (coins arrondis), en points : sert aux vérifications."""
    pts = []
    for a, b, c, r, _ in _rounded_corners(center):
        a0 = math.atan2(a[1] - c[1], a[0] - c[0]); a1 = math.atan2(b[1] - c[1], b[0] - c[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        pts += [(c[0] + r * math.cos(a0 + da * k / per_arc), c[1] + r * math.sin(a0 + da * k / per_arc))
                for k in range(per_arc + 1)]
    return pts

_GATES_REF = {
    # Tête
    64: (360, 148), 61: (389, 148), 63: (418, 148),
    # Ajna
    47: (360, 203), 24: (389, 203), 4: (418, 203),
    17: (360, 252), 11: (418, 252), 43: (388, 291),
    # Gorge
    62: (360, 358), 23: (389, 358), 56: (418, 358),
    16: (340, 394), 20: (340, 422),
    35: (437, 394), 12: (437, 422), 45: (437, 450),
    31: (360, 462), 8: (389, 462), 33: (418, 462),
    # G
    1: (389, 523), 7: (360, 548), 13: (418, 548),
    10: (327, 585), 25: (448, 588),
    15: (360, 620), 46: (418, 620), 2: (389, 646),
    # Cœur
    21: (539, 635), 51: (522, 652), 26: (497, 684), 40: (568, 699),
    # Sacral
    5: (360, 767), 14: (389, 767), 29: (418, 767),
    34: (340, 793), 27: (341, 838), 59: (437, 838),
    42: (360, 862), 3: (389, 862), 9: (418, 862),
    # Racine
    53: (360, 929), 60: (389, 929), 52: (418, 929),
    54: (341, 954), 38: (341, 984), 58: (341, 1014),
    19: (437, 954), 39: (437, 984), 41: (437, 1014),
    # Rate
    48: (107, 745), 57: (135, 760), 44: (164, 785), 50: (195, 805),
    32: (164, 826), 28: (138, 843), 18: (115, 859),
    # Plexus solaire
    36: (671, 745), 22: (643, 760), 37: (614, 785), 6: (583, 805),
    49: (614, 826), 55: (640, 843), 30: (663, 859),
}
GATE_POS = {g: _S(*p) for g, p in _GATES_REF.items()}

# Point de jonction du circuit d'intégration, et tronçon propre à chaque porte
# (une ou plusieurs courbes de Bézier, de la porte vers J).
_J = (166, 628)
# Les quatre tronçons partagent la même tangente au point J (direction _D) :
# ils s'y fondent comme des rails qui se rejoignent, sans élargir le trait.
# Tracés ajustés sur la référence avec cette tangente imposée (écart ≤ 4 px).
_D = (-0.35, 0.94)
_INTEGRATION_REF = {
    10: [((327, 585), (293.3, 590.2), (181.6, 586.2), (166, 628))],
    20: [((340, 422), (254.8, 451.1), (197.1, 544.5), (166, 628))],
    34: [((340, 793), (282.1, 784.8), (207.9, 770.4), (169.5, 720)), ((169.5, 720), (150.4, 695), (155.7, 655.8), (166, 628))],
    57: [((135, 760), (137.1, 714.4), (150.2, 670.4), (166, 628))],
}


INTEGRATION = {g: [tuple(_S(*p) for p in seg) for seg in segs] for g, segs in _INTEGRATION_REF.items()}
INTEGRATION_CHANNELS = {(10, 20), (10, 34), (10, 57), (20, 34), (20, 57), (34, 57)}

# Courbes ajustées par moindres carrés sur le trajet relevé dans la référence.
# Autres canaux courbes : deux points de contrôle (dans l'ordre de la clé :
# plus petite porte → plus grande). Absents de la table = canal droit.
_CURVES_REF = {
    (16, 48): ((197.2, 445.5), (125, 603.6)),
    (35, 36): ((580.5, 447.3), (646.2, 604.6)),
    (12, 22): ((563.6, 476.1), (623.1, 629.2)),
    (21, 45): ((521.1, 565.5), (496.5, 493.3)),
    (25, 51): ((477.7, 601.7), (508.2, 621.1)),
    (27, 50): ((290.6, 838.7), (240.4, 826.6)),
    (6, 59): ((537, 824.9), (487.4, 838.2)),
    (26, 44): ((380.3, 696.3), (229.3, 669.5)),
    (32, 54): ((187.5, 901), (263.2, 953.6)),
    (28, 38): ((168.2, 926.1), (249.6, 989.6)),
    (18, 58): ((146.7, 955.8), (242.5, 1015.8)),
    (19, 49): ((517, 954.7), (583.9, 896.5)),
    (39, 55): ((528.7, 988.6), (606.2, 923.6)),
    (30, 41): ((628.6, 952.1), (535.4, 1015.9)),
}
CHANNEL_CURVES = {k: (_S(*a), _S(*b)) for k, (a, b) in _CURVES_REF.items()}

OFFSET = (108, 24)         # position du bodygraph dans la page
PAGE_W, PAGE_H = 616, 840  # taille de la page (avec colonnes et légende)


def _centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def gate_label(gate):
    """Centre de la pastille du numéro de porte (et point de départ du canal)."""
    return GATE_POS[gate]


def _inside(pt, poly):
    x, y = pt
    inside = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _dist_to_boundary(pt, poly):
    best = float("inf")
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = x2 - x1, y2 - y1
        t = max(0, min(1, ((pt[0] - x1) * dx + (pt[1] - y1) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(pt[0] - (x1 + t * dx), pt[1] - (y1 + t * dy)))
    return best


def _channel_key(a, b):
    return (min(a, b), max(a, b))


def _split(p0, p1, p2, p3):
    """Coupe une courbe de Bézier en deux moitiés exactes (de Casteljau, t = 0,5)."""
    mid = lambda u, v: ((u[0] + v[0]) / 2, (u[1] + v[1]) / 2)
    a, b, c = mid(p0, p1), mid(p1, p2), mid(p2, p3)
    d, e = mid(a, b), mid(b, c)
    m = mid(d, e)
    return (p0, a, d, m), (m, e, c, p3)


def channel_halves(a, b):
    """Les deux moitiés d'un canal : (courbes côté porte a, courbes côté porte b).

    Chaque moitié part de sa porte. Elle prendra la couleur de cette porte.
    """
    key = _channel_key(a, b)
    if key in INTEGRATION_CHANNELS:
        return INTEGRATION[a], INTEGRATION[b]
    p0, p3 = GATE_POS[a], GATE_POS[b]
    if key in CHANNEL_CURVES:
        c1, c2 = CHANNEL_CURVES[key]
        if a != key[0]:
            c1, c2 = c2, c1
    else:  # droit
        c1 = (p0[0] + (p3[0] - p0[0]) / 3, p0[1] + (p3[1] - p0[1]) / 3)
        c2 = (p0[0] + 2 * (p3[0] - p0[0]) / 3, p0[1] + 2 * (p3[1] - p0[1]) / 3)
    half_a, half_b = _split(p0, c1, c2, p3)
    return [half_a], [half_b[::-1]]


def _bez_at(bez, t):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = bez
    u = 1 - t
    return (u**3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x3,
            u**3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y3)


def _samples(a, b, n=40):
    ha, hb = channel_halves(a, b)
    pts = []
    for seg in ha + hb:
        pts += [_bez_at(seg, i / n) for i in range(n + 1)]
    return pts


@functools.lru_cache(maxsize=1)  # le gabarit est fixe : une vérification suffit
def validate_template():
    """Vérifie le gabarit. Lève une erreur au moindre écart.

    1. Mêmes portes, mêmes centres, mêmes canaux que le moteur.
    2. Chaque pastille de porte tient entière dans son centre, sans en chevaucher une autre.
    3. Chaque moitié de canal part exactement de sa porte.
    4. Aucun canal ne passe à travers un centre qui n'est pas le sien.
    5. Deux canaux sans porte commune ne se superposent jamais sur leur longueur.
    6. Au carrefour du circuit d'intégration, les tronçons se rejoignent dans
       la même direction, pour que l'épaisseur du trait reste constante.
    """
    problems = []
    if set(GATE_POS) != set(D.GATE_CENTER):
        problems.append(f"portes manquantes ou en trop : {sorted(set(D.GATE_CENTER) ^ set(GATE_POS))}")
    keys = {_channel_key(*c) for c in D.CHANNELS}
    for k in list(CHANNEL_CURVES) + list(INTEGRATION_CHANNELS):
        if k not in keys:
            problems.append(f"tracé {k[0]}-{k[1]} ne correspond à aucun canal du moteur")
    if problems:
        raise ValueError("Gabarit invalide :\n  " + "\n  ".join(problems))

    for g, pt in GATE_POS.items():
        poly = center_outline(D.GATE_CENTER[g])
        if not _inside(pt, poly) or _dist_to_boundary(pt, poly) < 6:
            problems.append(f"pastille de la porte {g} déborde de son centre")
    for gates in D.CENTERS.values():
        for i, g1 in enumerate(gates):
            for g2 in gates[i + 1:]:
                if math.dist(GATE_POS[g1], GATE_POS[g2]) < 13:
                    problems.append(f"numéros {g1} et {g2} se chevauchent")

    samples = {}
    for a, b in D.CHANNELS:
        ha, hb = channel_halves(a, b)
        if math.dist(ha[0][0], GATE_POS[a]) > 0.5 or math.dist(hb[0][0], GATE_POS[b]) > 0.5:
            problems.append(f"canal {a}-{b} ne part pas de ses portes")
        own = {D.GATE_CENTER[a], D.GATE_CENTER[b]}
        pts = _samples(a, b)
        samples[(a, b)] = pts
        for p in pts:
            hit = next((c for c in CENTER_SHAPES
                        if c not in own and _inside(p, center_outline(c, 4))), None)
            if hit:
                problems.append(f"canal {a}-{b} passe à travers le centre {hit}")
                break

    J = _S(*_J)
    # 6. Carrefour : tous les tronçons touchent J avec la même direction
    #    (sinon le trait s'épaissit là où ils se rejoignent).
    for g, segs in INTEGRATION.items():
        last = segs[-1]
        if math.dist(last[3], J) > 0.01:
            problems.append(f"le tronçon de la porte {g} n'arrive pas au carrefour")
            continue
        tx, ty = last[3][0] - last[2][0], last[3][1] - last[2][1]
        n = math.hypot(tx, ty)
        cos = abs((tx * _D[0] + ty * _D[1]) / (n * math.hypot(*_D)))
        if cos < math.cos(math.radians(3)):
            problems.append(f"le tronçon de la porte {g} arrive de biais au carrefour (épaisseur irrégulière)")
    near_j = lambda p: math.dist(p, J) < 36
    chans = list(samples)
    for i, c1 in enumerate(chans):
        for c2 in chans[i + 1:]:
            if set(c1) & set(c2):
                continue
            both_int = {_channel_key(*c1), _channel_key(*c2)} <= INTEGRATION_CHANNELS
            run = longest = 0.0
            prev = None
            for p in samples[c1]:
                if both_int and near_j(p):  # carrefour : les tronçons s'y rejoignent par construction
                    run, prev = 0.0, p
                    continue
                close = min(math.dist(p, q) for q in samples[c2]) < 7
                run = run + (math.dist(p, prev) if prev and close else 0) if close else 0.0
                longest = max(longest, run)
                prev = p
            if longest > 26:
                problems.append(f"canaux {c1[0]}-{c1[1]} et {c2[0]}-{c2[1]} se superposent")
    if problems:
        raise ValueError("Gabarit invalide :\n  " + "\n  ".join(problems))
    return True


# --------------------------------------------------------------------------- données

def derive(active_gates):
    """Canaux et centres définis, déduits exactement comme dans hd.chart."""
    active = {int(g): set(s) for g, s in active_gates.items()}
    channels = [(a, b) for a, b in D.CHANNELS if a in active and b in active]
    defined = {D.GATE_CENTER[g] for ch in channels for g in ch}
    return active, channels, defined


# --------------------------------------------------------------------------- habillages

# Couleurs : toutes dans hd/themes.py. SKINS : thèmes proposés par « skin » (API, golden
# files) ; EXTRA_SKINS : thèmes réservés (composite) ou proposés par « theme » (gdh).
SKINS = {k: THEMES[k] for k in ("classique", "atlas")}
EXTRA_SKINS = {k: v for k, v in THEMES.items() if k not in SKINS}

FONT = "Inter, 'Helvetica Neue', Arial, sans-serif"
SYMBOLS = "'DejaVu Sans', 'Segoe UI Symbol', 'Apple Symbols', sans-serif"  # glyphes des planètes


# Polices de l'habillage « atlas » (sous-ensembles WOFF2, SIL OFL 1.1 : voir fonts/OFL.txt).
EMBEDDED_FONTS = (
    ("Instrument Serif", "italic", 400, "instrument-serif-italic.woff2"),
    ("Jost", "normal", 400, "jost-400.woff2"),
    ("Jost", "italic", 300, "jost-300-italic.woff2"),
    ("Space Grotesk", "normal", 500, "space-grotesk-500.woff2"),
    ("Space Grotesk", "normal", 600, "space-grotesk-600.woff2"),
)

# Largeur des caractères de la phrase de résumé en Jost 400 (en em), pour réduire la taille
# de la phrase seulement quand elle ne tiendrait pas dans la page.
_JOST_ADVANCE = {
    ' ': 0.3, '(': 0.31, ')': 0.31, ',': 0.308, '-': 0.21, '/': 0.515, '0': 0.6, '1': 0.45, '2': 0.569,
    '3': 0.546, '4': 0.583, '5': 0.564, '6': 0.576, '7': 0.525, '8': 0.546, '9': 0.576, 'A': 0.66, 'E': 0.55,
    'G': 0.775, 'H': 0.715, 'I': 0.245, 'L': 0.45, 'M': 0.81, 'O': 0.79, 'P': 0.548, 'R': 0.56, 'S': 0.548,
    'a': 0.481, 'c': 0.478, 'd': 0.57, 'e': 0.515, 'f': 0.286, 'g': 0.57, 'i': 0.26, 'j': 0.25, 'l': 0.23,
    'm': 0.78, 'n': 0.525, 'o': 0.546, 'p': 0.57, 'q': 0.57, 'r': 0.343, 's': 0.403, 't': 0.24, 'u': 0.525,
    'v': 0.44, 'x': 0.42, 'y': 0.44, 'É': 0.55, 'à': 0.485, 'è': 0.515, 'é': 0.515,
}
SUMMARY_SIZE, SUMMARY_MAX_WIDTH = 16, PAGE_W - 40


def summary_font_size(text: str) -> float:
    """16 px, ou moins si la phrase dépasserait la largeur utile (une décimale, arrondie vers le bas)."""
    em = sum(_JOST_ADVANCE.get(ch, max(_JOST_ADVANCE.values())) for ch in text)
    if em * SUMMARY_SIZE <= SUMMARY_MAX_WIDTH:
        return SUMMARY_SIZE
    return math.floor(SUMMARY_MAX_WIDTH / em * 10) / 10


@functools.lru_cache(maxsize=1)
def _font_faces():
    """@font-face embarqués en base64 : la carte s'affiche pareil partout (page, e-mail, PNG)."""
    import base64
    from pathlib import Path
    here = Path(__file__).with_name("fonts")
    css = []
    for family, style, weight, file in EMBEDDED_FONTS:
        data = base64.b64encode((here / file).read_bytes()).decode()
        css.append(f"@font-face{{font-family:'{family}';font-style:{style};font-weight:{weight};"
                   f"src:url(data:font/woff2;base64,{data}) format('woff2')}}")
    return "<style>" + "".join(css) + "</style>"


# --------------------------------------------------------------------------- rendu

def _pt(p):
    return f"{p[0] + OFFSET[0]:.1f},{p[1] + OFFSET[1]:.1f}"


def _path(bez):
    p0, c1, c2, p3 = bez
    return f"M{_pt(p0)} C{_pt(c1)} {_pt(c2)} {_pt(p3)}"


def _center_path(center):
    """Contour SVG du centre avec de vrais arcs de cercle aux coins."""
    out = []
    for a, b, c, r, sweep in _rounded_corners(center):
        out.append(("L" if out else "M") + _pt(a))
        out.append(f"A{r:.2f},{r:.2f} 0 0 {sweep} {_pt(b)}")
    return " ".join(out) + " Z"


# Profil des veines : fines bandes (un seul pas de la table sur 25) au milieu du bruit.
_VEINS = (0,) * 8 + (0.5, 0, 0, 0, 1, 0, 0, 0, 0.7) + (0,) * 8


class _Paints:
    """Transforme une couleur du thème en valeur d'attribut SVG. Un Gradient ou un Marble
    est déclaré une seule fois dans la carte, sous l'identifiant « {uid}-{nom} »."""

    def __init__(self, uid):
        self.uid, self.defs = uid, {}

    def __call__(self, paint):
        if isinstance(paint, Gradient):
            self.defs.setdefault(paint.name, self._gradient(paint))
            return f"url(#{self.uid}-{paint.name})"
        return paint

    def filter(self, marble: Marble) -> str:
        self.defs.setdefault(marble.name, self._marble(marble))
        return f"url(#{self.uid}-{marble.name})"

    def _gradient(self, g):
        box = (f'gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{PAGE_H}"' if g.units == "page"
               else 'x1="0" y1="0" x2="0" y2="1"')
        stops = "".join(f'<stop offset="{o:g}" stop-color="{c}"/>' for o, c in g.stops)
        return f'<linearGradient id="{self.uid}-{g.name}" {box}>{stops}</linearGradient>'

    def _marble(self, m):
        # Bruit fractal → veines : la table ne garde que des bandes étroites du bruit (les
        # veines), à l'opacité m.opacity au plus ; « in » les limite à la forme filtrée.
        r, g, b = m.color
        k = m.opacity
        table = " ".join(f"{v * k:g}" for v in _VEINS)
        return (f'<filter id="{self.uid}-{m.name}" x="0" y="0" width="100%" height="100%" '
                f'color-interpolation-filters="sRGB">'
                f'<feTurbulence type="fractalNoise" baseFrequency="{m.base_frequency}" '
                f'numOctaves="{m.octaves}" seed="{m.seed}"/>'
                f'<feColorMatrix type="matrix" values="0 0 0 0 {r} 0 0 0 0 {g} 0 0 0 0 {b} 1 0 0 0 0"/>'
                f'<feComponentTransfer><feFuncA type="table" tableValues="{table}"/></feComponentTransfer>'
                f'<feComposite in2="SourceAlpha" operator="in"/></filter>')

    def block(self):
        return f'<defs>{"".join(self.defs.values())}</defs>' if self.defs else ""


def _background(s, uid, paint):
    bg = s["background"]
    if bg["kind"] == "plain":
        return f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="{bg["color"]}"/>'
    if bg["kind"] == "marble":
        return (f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="{bg["color"]}"/>\n'
                f'  <rect width="{PAGE_W}" height="{PAGE_H}" fill="{bg["color"]}" '
                f'filter="{paint.filter(bg["texture"])}"/>')
    return _atmosphere(bg, uid)


def _atmosphere(bg, uid):
    ox, oy = OFFSET
    return f"""
  <defs>
    <linearGradient id="{uid}-bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{bg['top']}"/><stop offset="1" stop-color="{bg['bottom']}"/>
    </linearGradient>
    <radialGradient id="{uid}-halo" cx="0.5" cy="0.42" r="0.5">
      <stop offset="0" stop-color="{bg['halo']}" stop-opacity="0.85"/>
      <stop offset="1" stop-color="{bg['halo']}" stop-opacity="0"/>
    </radialGradient>
    <filter id="{uid}-soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="7"/></filter>
    <filter id="{uid}-glow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect width="{PAGE_W}" height="{PAGE_H}" fill="url(#{uid}-bg)"/>
  <ellipse cx="{200 + ox}" cy="{350 + oy}" rx="250" ry="350" fill="url(#{uid}-halo)"/>
  <g fill="none" stroke="{bg['orbit']}" stroke-opacity="0.16" stroke-width="0.8">
    <ellipse cx="{200 + ox}" cy="{330 + oy}" rx="262" ry="112" transform="rotate(-16 {200 + ox} {330 + oy})"/>
    <ellipse cx="{200 + ox}" cy="{400 + oy}" rx="290" ry="200" transform="rotate(12 {200 + ox} {400 + oy})"/>
  </g>
  <circle cx="{PAGE_W - 70}" cy="{548 + oy}" r="6" fill="{bg['dot_violet']}" fill-opacity="0.5"/>
  <circle cx="{66}" cy="{560 + oy}" r="4" fill="{bg['dot_orange']}" fill-opacity="0.7"/>
  <circle cx="{PAGE_W - 120}" cy="{20}" r="2.5" fill="{bg['dot_orange']}" fill-opacity="0.6"/>
  <path filter="url(#{uid}-soft)" fill="{bg['veil']}" fill-opacity="0.55"
        d="M{200 + ox},{0 + oy} C{268 + ox},{0 + oy} {284 + ox},{90 + oy} {272 + ox},{150 + oy}
           C{264 + ox},{188 + oy} {250 + ox},{198 + oy} {248 + ox},{216 + oy}
           C{306 + ox},{232 + oy} {376 + ox},{258 + oy} {394 + ox},{340 + oy}
           L{406 + ox},{598 + oy} C{408 + ox},{650 + oy} {340 + ox},{672 + oy} {200 + ox},{674 + oy}
           C{60 + ox},{672 + oy} {-8 + ox},{650 + oy} {-6 + ox},{598 + oy}
           L{6 + ox},{340 + oy} C{24 + ox},{258 + oy} {94 + ox},{232 + oy} {152 + ox},{216 + oy}
           C{150 + ox},{198 + oy} {136 + ox},{188 + oy} {128 + ox},{150 + oy}
           C{116 + ox},{90 + oy} {132 + ox},{0 + oy} {200 + ox},{0 + oy} Z"/>"""


def _planet_columns(chart, s):
    if chart is None or not getattr(chart, "design", None):
        return ""
    num, title = s["font_num"], s["font_title"]
    w = f' font-weight="{s["num_weights"][1]}"' if "num_weights" in s else ""
    out = []
    y0, step = 70 + OFFSET[1], 34
    out.append(f'<text x="22" y="{y0 - 30}" font-family="{title}" font-style="italic" font-size="14" '
               f'fill="{s["design_text"]}">Design</text>')
    out.append(f'<text x="{PAGE_W - 22}" y="{y0 - 30}" font-family="{title}" font-style="italic" '
               f'font-size="14" text-anchor="end" fill="{s["personality_text"]}">Personnalité</text>')
    for i, planet in enumerate(D.PLANETS):
        y = y0 + i * step
        d, p = chart.design[planet], chart.personality[planet]
        glyph = escape(D.PLANET_GLYPHS[planet])
        out.append(f'<text x="22" y="{y}" fill="{s["design_text"]}">'
                   f'<tspan font-family="{SYMBOLS}" font-size="13">{glyph}</tspan>'
                   f'<tspan dx="7" font-family="{num}" font-size="15"{w}>{d.gate}.{d.line}</tspan></text>')
        out.append(f'<text x="{PAGE_W - 22}" y="{y}" text-anchor="end" fill="{s["personality_text"]}">'
                   f'<tspan font-family="{num}" font-size="15"{w}>{p.gate}.{p.line}</tspan>'
                   f'<tspan dx="7" font-family="{SYMBOLS}" font-size="13">{glyph}</tspan></text>')
    return "\n  ".join(out)


def summary_sentence(chart) -> str:
    """« Générateur à autorité sacrale, profil 5/1 (Hérétique / Investigateur) »"""
    t = D.TYPES_FR[chart.type][0]
    auth = D.AUTHORITY_FR[chart.authority]
    auth = auth[0].lower() + auth[1:]
    pl, dl = (int(x) for x in chart.profile.split("/"))
    return f"{t} à autorité {auth}, profil {chart.profile} ({D.LINE_NAMES_FR[pl]} / {D.LINE_NAMES_FR[dl]})"


# Caractères interdits en XML 1.0 (contrôles, demi-caractères Unicode isolés…).
_XML_INVALID = re.compile("[^\u0009\u000a\u000d\u0020-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")


def _xml_text(text: str) -> str:
    """Texte libre (prénom) prêt pour le SVG : caractères interdits retirés, blancs
    regroupés, puis échappé (<, &, guillemets)."""
    return escape(" ".join(_XML_INVALID.sub("", text).split()))


def _caption(chart, name, s, uid):
    if chart is None:
        return ""
    title, text, cx = s["font_title"], s["font_text"], PAGE_W / 2
    y = 700 + OFFSET[1]
    out = []
    who = name or chart.name or ""
    if who and s.get("name_gradient"):  # prénom en dégradé orange → violet (Design → Personnalité)
        out.append(f'<defs><linearGradient id="{uid}-prenom" x1="0" x2="1">'
                   f'<stop offset="0" stop-color="{s["design_text"]}"/><stop offset="1" stop-color="{s["personality_text"]}"/>'
                   f'</linearGradient></defs>'
                   f'<text x="{cx}" y="{y}" font-family="{title}" font-style="italic" font-size="30" '
                   f'text-anchor="middle" fill="url(#{uid}-prenom)">{_xml_text(who)}</text>')
        y += 20
    elif who:
        out.append(f'<text x="{cx}" y="{y}" font-family="{title}" font-style="italic" font-size="30" '
                   f'font-weight="500" text-anchor="middle" fill="{s["text"]}">{_xml_text(who)}</text>')
        y += 20
    if s.get("legend"):  # filet orange → violet : rappelle les deux faces de la carte
        out.append(f'<defs><linearGradient id="{uid}-filet" x1="0" x2="1">'
                   f'<stop offset="0" stop-color="{s["design_text"]}"/><stop offset="1" stop-color="{s["personality_text"]}"/>'
                   f'</linearGradient></defs>'
                   f'<rect x="{cx - 28}" y="{y - 6}" width="56" height="2" rx="1" fill="url(#{uid}-filet)"/>')
        y += 20
    sentence = summary_sentence(chart)
    size = summary_font_size(sentence) if s.get("embed_fonts") else 16
    out.append(f'<text x="{cx}" y="{y}" font-family="{text}" font-size="{size:g}" text-anchor="middle" '
               f'fill="{s["text"]}">{escape(sentence)}</text>')
    if s.get("legend"):
        y += 26
        out.append(f'<text x="{cx}" y="{y}" font-family="{text}" font-style="italic" font-weight="300" '
                   f'font-size="11.5" text-anchor="middle" fill="{s["muted"]}">'
                   f'<tspan fill="{s["design_text"]}">{s["legend_design"]}</tspan> : Design, ce qui agit en toi sans que tu le voies  ·  '
                   f'<tspan fill="{s["personality_text"]}">{s["legend_personality"]}</tspan> : Personnalité, ce que tu connais de toi</text>')
    return "\n  ".join(out)


def _halo(s) -> str:
    """Fin contour sombre sous le texte (dessiné avant le remplissage), si le thème en a un."""
    h = s.get("text_halo")
    if not h:
        return ""
    return (f' stroke="{h["color"]}" stroke-opacity="{h["opacity"]}" stroke-width="{h["width"]}" '
            f'stroke-linejoin="round" paint-order="stroke"')


def new_uid() -> str:
    """Préfixe des identifiants internes d'une carte (commence par une lettre, comme l'exige XML)."""
    return "hd" + secrets.token_hex(4)


def render_bodygraph(chart=None, *, active_gates=None, skin="atlas", theme=None, name=None,
                     show_planets=True, show_caption=True, uid=None) -> str:
    """Rend le bodygraph en SVG.

    chart : objet Chart du moteur (hd.chart.build_chart). Ou bien active_gates :
    {porte: ["design"] | ["personality"] | ["design", "personality"]}.

    theme (ou skin, son ancien nom) : un thème de hd.themes.THEMES. Ne change que l'apparence.

    uid : préfixe des identifiants internes (dégradés, filtres, centres). Tiré au
    hasard par défaut, pour que plusieurs cartes puissent cohabiter dans une même
    page HTML sans se voler leurs dégradés. À fixer pour un rendu reproductible.
    Un thème qui a un id_prefix le place devant (ex. « gdh-hd1a2b3c4d »).
    """
    s = THEMES[theme or skin]
    uid = uid or new_uid()
    if s.get("id_prefix"):
        uid = f"{s['id_prefix']}-{uid}"
    validate_template()
    if chart is not None:
        active_gates = chart.active_gates
    if active_gates is None:
        raise ValueError("fournir chart ou active_gates")
    active, channels, defined = derive(active_gates)
    if chart is not None:  # garde-fou : le dessin doit dire la même chose que le moteur
        assert sorted(_channel_key(*c) for c in channels) == sorted(_channel_key(*c) for c in chart.channels)
        assert defined == set(chart.defined_centers)

    paint = _Paints(uid)
    design, personality = paint(s["design"]), paint(s["personality"])
    w = 6.2
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PAGE_W} {PAGE_H}" '
             f'width="{PAGE_W}" height="{PAGE_H}" font-family="{FONT}" role="img" '
             f'aria-label="Bodygraph Human Design"'
             # Polices embarquées : positions exactes des lettres, sans arrondi à petite taille.
             + (' text-rendering="geometricPrecision">' if s.get("embed_fonts") else '>')]
    if s.get("embed_fonts"):
        parts.append(_font_faces())
    defs_at = len(parts)  # dégradés et filtres du thème (rien pour atlas et classique)
    parts.append(_background(s, uid, paint))

    # 1. Canaux : fond (canal ouvert), puis moitiés activées, chacune de la couleur de sa porte.
    halves = {c: channel_halves(*c) for c in D.CHANNELS}
    seg_d = lambda segs: " ".join(_path(seg) for seg in segs)
    parts.append('<g fill="none" stroke-linecap="butt">')
    if s["channel_edge"]:
        for ha, hb in halves.values():
            parts.append(f'<path d="{seg_d(ha)} {seg_d(hb)}" stroke="{s["channel_edge"]}" '
                         f'stroke-width="{w + 2.2}" stroke-linecap="round"/>')
    for ha, hb in halves.values():
        parts.append(f'<path d="{seg_d(ha)} {seg_d(hb)}" stroke="{s["channel_inactive"]}" stroke-width="{w}"/>')
    drawn = set()
    for (a, b), (ha, hb) in halves.items():
        for gate, half in ((a, ha), (b, hb)):
            sides = active.get(gate, set())
            d = seg_d(half)
            if not sides or (gate, d) in drawn:
                continue  # tronçon partagé (circuit d'intégration) : dessiné une fois
            drawn.add((gate, d))
            cls = f'class="gate-{gate}"'
            if sides == {"design"}:
                parts.append(f'<path {cls} d="{d}" stroke="{design}" stroke-width="{w}"/>')
            elif sides == {"personality"}:
                parts.append(f'<path {cls} d="{d}" stroke="{personality}" stroke-width="{w}"/>')
            else:  # les deux : rayé Design / Personnalité
                parts.append(f'<path {cls} d="{d}" stroke="{design}" stroke-width="{w}"/>')
                parts.append(f'<path {cls} d="{d}" stroke="{personality}" stroke-width="{w}" '
                             f'stroke-dasharray="{s["both_dash"]}"/>')
    parts.append('</g>')

    # 3. Centres.
    fills = s["center_defined"]
    for center in D.CENTERS:
        d = _center_path(center)
        if center in defined:
            fill = paint(fills[center] if isinstance(fills, dict) else fills)
            glow = f' filter="url(#{uid}-glow)"' if s["center_glow"] else ""
            parts.append(f'<path id="{uid}-center-{center}" d="{d}" fill="{fill}" '
                         f'stroke="{s["center_stroke"]}" stroke-width="1.6"{glow}/>')
            if s["center_texture"]:  # veinage par-dessus, limité à la forme du centre
                parts.append(f'<path d="{d}" fill="{fill}" filter="{paint.filter(s["center_texture"])}"/>')
        else:
            parts.append(f'<path id="{uid}-center-{center}" d="{d}" fill="{s["center_open"]}" '
                         f'stroke="{s["center_open_stroke"]}" stroke-width="1.2"/>')

    # 4. Numéros de portes.
    num = s["font_num"]
    w_on, w_off = s.get("num_weights", (700, 500))
    for g in sorted(GATE_POS):
        x, y = gate_label(g)
        x, y = x + OFFSET[0], y + OFFSET[1]
        if g in active:
            r = 6.8
            sides = active[g]
            flat = s.get("gate_pastille")  # aplats propres aux pastilles, sinon les couleurs des canaux
            d_fill, p_fill = (flat["design"], flat["personality"]) if flat else (design, personality)
            if s["gate_on"]:  # une seule couleur de pastille (classique)
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{s["gate_on"]}"/>')
            elif sides == {"design", "personality"}:  # moitié Design, moitié Personnalité
                parts.append(f'<path d="M{x:.1f},{y - r:.1f} A{r},{r} 0 0 0 {x:.1f},{y + r:.1f} Z" fill="{d_fill}"/>')
                parts.append(f'<path d="M{x:.1f},{y - r:.1f} A{r},{r} 0 0 1 {x:.1f},{y + r:.1f} Z" fill="{p_fill}"/>')
            else:
                col = d_fill if sides == {"design"} else p_fill
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}"/>')
            if s.get("gate_ring"):
                ring, rw = s["gate_ring"]
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="none" stroke="{ring}" stroke-width="{rw}"/>')
            halo = _halo(s) if sides == {"design", "personality"} else ""
            parts.append(f'<text x="{x:.1f}" y="{y + 2.9:.1f}" font-family="{num}" font-size="8.4" '
                         f'font-weight="{w_on}" text-anchor="middle" fill="{s["gate_text_on"]}"{halo}>{g}</text>')
        else:
            center = D.GATE_CENTER[g]
            on_color = center in defined
            fill = s["gate_text_defined"] if on_color else s["gate_text"]
            halo = ""
            if fill == "auto":  # ivoire ou brun selon la couleur du centre défini
                under = fills[center] if isinstance(fills, dict) else solid(fills)
                fill = text_on(under, s["text_choices"])
                if fill == s["text_choices"][0] and contrast(fill, under) < MIN_CONTRAST:
                    halo = _halo(s)  # ivoire encore trop peu contrasté : contour sombre
            opacity = s["gate_text_defined_opacity"] if on_color else None
            op = f' fill-opacity="{opacity}"' if opacity is not None else ""
            parts.append(f'<text x="{x:.1f}" y="{y + 2.8:.1f}" font-family="{num}" font-size="8" '
                         f'font-weight="{w_off}" text-anchor="middle" fill="{fill}"{op}{halo}>{g}</text>')

    if show_planets:
        parts.append(_planet_columns(chart, s))
    if show_caption:
        parts.append(_caption(chart, name, s, uid))
    parts.insert(defs_at, paint.block())
    parts.append('</svg>')
    return "\n  ".join(p for p in parts if p)
