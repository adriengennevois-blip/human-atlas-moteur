# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Ingressions : les changements de porte et de ligne de chaque corps, sur un intervalle libre.

Les ingressions ne dépendent de personne : elles sont calculées par JOUR UTC et gardées en
mémoire (cache). Une fenêtre quelconque (24 h, 7 j, 28 j, 1 an) est assemblée à partir de ces
journées ; deux fenêtres qui se recouvrent partagent donc leur calcul.

Méthode (rapide : 2 à 4 appels d'éphéméride par changement) : à chaque pas, on prédit l'instant
où le corps atteindra la prochaine frontière de ligne d'après sa vitesse (Newton), on mesure sa
position à cet instant, et dès que la frontière est franchie on resserre par fausse position
(Illinois) jusqu'à 1e-7 degré, soit bien moins qu'une seconde pour la Lune. Un corps presque
arrêté (station) avance par petits pas, rétrogradation comprise.

La Terre et le Nœud Sud sont à 180° du Soleil et du Nœud Nord, soit exactement 192 lignes : ils
changent aux mêmes instants, sans calcul supplémentaire.
"""
import functools
from datetime import date, datetime, timedelta, timezone

from . import data as D
from .chart import activation
from .ephemeris import jd_to_datetime, julian_day, lon_speed

LINES = 384                       # 64 portes × 6 lignes
HALF_TURN = LINES // 2            # 180° en lignes
MAX_DAYS = 366                    # intervalle maximal d'une requête
TOLERANCE_DAYS = 1e-6             # précision de chaque instant : 0,09 s, quelle que soit la vitesse du corps
AIM_DAYS = 5e-7                   # on vise juste après la frontière : 0,04 s après son franchissement
SLOW = 0.02                       # °/jour : en dessous, le corps est presque à l'arrêt
BASES = ("sun", "moon", "north_node", "mercury", "venus", "mars", "jupiter", "saturn", "uranus",
         "neptune", "pluto")
TWIN = {"earth": "sun", "south_node": "north_node"}   # corps à 180° d'un autre


def _wrap(delta: float) -> float:
    return (delta + 180.0) % 360.0 - 180.0


def line_of(n: int) -> tuple[int, int]:
    """(porte, ligne) de la n-ième ligne de la roue (n modulo 384, à partir de la porte 41.1)."""
    n %= LINES
    return D.GATE_ORDER[n // 6], n % 6 + 1


@functools.lru_cache(maxsize=1 << 16)
def _edge(jd: float, body: str) -> tuple[float, float]:
    """Position et vitesse à minuit UTC : la fin d'une journée est le début de la suivante, un seul calcul."""
    return lon_speed(jd, body)


class _Track:
    """Position d'un corps en degrés « dépliés » à partir du début de la roue (pas de saut à 360°)."""

    def __init__(self, body: str, jd: float):
        self.body = body
        self.lon, self.speed = _edge(jd, body)
        self.y = (self.lon - D.WHEEL_START) % 360.0
        self.jd = jd
        self.accel = 0.0          # °/jour² : estimée d'un pas à l'autre, affine la prédiction

    def at(self, jd: float) -> tuple[float, float]:
        """(y, vitesse) à jd, sans modifier la piste."""
        lon, speed = lon_speed(jd, self.body)
        return self.y + _wrap(lon - self.lon), speed

    def move(self, jd: float, y: float, speed: float) -> None:
        if jd > self.jd + 1e-9:
            self.accel = (speed - self.speed) / (jd - self.jd)
        self.lon = (D.WHEEL_START + y) % 360.0
        self.y, self.speed, self.jd = y, speed, jd

    def eta(self, target: float) -> float:
        """Jours avant d'atteindre « target » : vitesse et accélération supposées constantes."""
        d, v, a = target - self.y, self.speed, self.accel
        disc = v * v + 2 * a * d
        if a == 0.0 or disc <= 0.0 or v == 0.0:
            return d / v if v != 0.0 else 0.1
        root = disc ** 0.5
        return 2 * d / (v + root if v > 0 else v - root)


def _refine(track: _Track, tb: float, yb: float, vb: float, boundary: float, forward: bool, tol: float):
    """Instant (juste après la frontière) où la piste franchit « boundary » entre son état actuel
    (avant la frontière) et (tb, yb, vb) (après)."""
    sign = 1.0 if forward else -1.0
    ta = track.jd
    fa = sign * (track.y - boundary)               # < 0 : pas encore franchie
    fb = sign * (yb - boundary)                    # ≥ 0 : franchie
    side = 0
    while True:
        if fb < tol or tb - ta < 1e-9:
            return tb, yb, vb
        t = tb - fb * (tb - ta) / (fb - fa)        # fausse position
        t = min(max(t, ta + 1e-9), tb)
        y, v = track.at(t)
        f = sign * (y - boundary)
        if f >= 0:
            tb, yb, vb, fb = t, y, v, f
            if side == 1:
                fa /= 2                            # Illinois : évite la convergence lente d'un seul côté
            side = 1
        else:
            ta, fa = t, f
            if side == -1:
                fb /= 2
            side = -1
        if abs(f) < tol and f >= 0:
            return t, y, v


def _crossings(body: str, jd_a: float, jd_b: float) -> tuple[int, list[tuple]]:
    """(ligne au début, [(jd, ligne avant, ligne après, rétrograde)]) pour jd_a < jd ≤ jd_b."""
    arc = D.LINE_ARC
    tr = _Track(body, jd_a)
    n = int(tr.y // arc)
    n_start, out = n, []
    while tr.jd < jd_b:
        v = tr.speed
        forward = v >= 0
        aim = max(abs(v) * AIM_DAYS, 1e-9)
        target = (n + 1) * arc + aim if forward else n * arc - aim
        dt = tr.eta(target) if abs(v) >= 1e-9 else 0.1
        cap = 1.0 if abs(v) > SLOW else 0.1        # près d'une station : petits pas
        dt = min(max(dt, 2e-6), cap)
        t2 = min(tr.jd + dt, jd_b)
        if t2 == jd_b:
            lon2, v2 = _edge(jd_b, tr.body)
            y2 = tr.y + _wrap(lon2 - tr.lon)
        else:
            y2, v2 = tr.at(t2)
        n2 = int(y2 // arc)
        if n2 != n:
            up = n2 > n
            boundary = (n + 1) * arc if up else n * arc
            t_star, y_star, v_star = _refine(tr, t2, y2, v2, boundary, up, max(abs(v) * TOLERANCE_DAYS, 1e-9))
            n_new = n + 1 if up else n - 1
            out.append((t_star, n, n_new, v_star < 0))
            tr.move(t_star, y_star, v_star)
            n = int(y_star // arc)
            if n != n_new:                         # garde-fou : on se recale sur la position réelle
                n = n_new
        else:
            tr.move(t2, y2, v2)
    return n_start, out


@functools.lru_cache(maxsize=4096)  # aucune donnée personnelle : une journée UTC sert à tous
def _day(ordinal: int) -> dict:
    """{corps: (ligne au début de la journée, ((jd, avant, après, rétrograde), …))} pour un jour UTC."""
    d = date.fromordinal(ordinal)
    jd_a = julian_day(datetime(d.year, d.month, d.day, tzinfo=timezone.utc))
    out = {}
    for body in BASES:
        n0, events = _crossings(body, jd_a, jd_a + 1.0)
        out[body] = (n0, tuple(events))
    for twin, base in TWIN.items():
        n0, events = out[base]
        out[twin] = (n0 + HALF_TURN, tuple((jd, a + HALF_TURN, b + HALF_TURN, r) for jd, a, b, r in events))
    return out


def clear_cache() -> None:
    _day.cache_clear()
    _edge.cache_clear()


def _jd(when: datetime) -> float:
    return julian_day(when.astimezone(timezone.utc))


def _check(start: datetime, end: datetime) -> None:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("début et fin doivent préciser leur fuseau")
    if end <= start:
        raise ValueError("la fin doit être postérieure au début")
    if end - start > timedelta(days=MAX_DAYS):
        raise ValueError(f"l'intervalle est limité à {MAX_DAYS} jours")


def events(start: datetime, end: datetime) -> list[dict]:
    """Tous les changements de ligne (donc de porte) de tous les corps sur ]début, fin], triés par heure.
    Chaque élément : {"jd", "planet", "from": (porte, ligne), "to": (porte, ligne), "retrograde"}."""
    _check(start, end)
    jd_s, jd_e = _jd(start), _jd(end)
    day0 = (start.astimezone(timezone.utc)).date().toordinal()
    out = []
    for ordinal in range(day0, end.astimezone(timezone.utc).date().toordinal() + 1):
        for planet, (_, evs) in _day(ordinal).items():
            for jd, a, b, retro in evs:
                if jd_s < jd <= jd_e:
                    out.append({"jd": jd, "planet": planet, "from": line_of(a), "to": line_of(b),
                                "retrograde": retro})
    out.sort(key=lambda e: (e["jd"], D.PLANETS.index(e["planet"])))
    return out


def _utc(jd: float) -> datetime:
    return jd_to_datetime(jd).replace(microsecond=0)


def iso(jd: float) -> str:
    """Instant UTC ISO 8601, à la seconde."""
    return _utc(jd).isoformat()


def ingresses(start: datetime, end: datetime, level: str = "line") -> dict:
    """La frise : pour chaque corps, porte.ligne au début puis chaque changement, en UTC.
    level « gate » ne garde que les changements de porte."""
    evs = events(start, end)
    jd_s = _jd(start)
    planets = {}
    for p in D.PLANETS:
        lon, _ = lon_speed(jd_s, p)
        a = activation(p, lon)
        planets[p] = {"at_start": {"gate": a.gate, "line": a.line, "label": f"{a.gate}.{a.line}"},
                      "changes": []}
    for e in evs:
        (g0, l0), (g1, l1) = e["from"], e["to"]
        kind = "gate" if g0 != g1 else "line"
        if level == "gate" and kind != "gate":
            continue
        planets[e["planet"]]["changes"].append({
            "utc": iso(e["jd"]), "kind": kind, "from": f"{g0}.{l0}", "to": f"{g1}.{l1}",
            "gate": g1, "line": l1, "retrograde": e["retrograde"]})
    return {"from_utc": start.astimezone(timezone.utc).replace(microsecond=0).isoformat(),
            "to_utc": end.astimezone(timezone.utc).replace(microsecond=0).isoformat(),
            "level": level, "count": sum(len(v["changes"]) for v in planets.values()), "planets": planets}
