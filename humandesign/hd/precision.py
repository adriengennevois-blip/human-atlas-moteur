# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Sensibilité du thème à l'heure de naissance.

Pour chaque activation (13 corps × Design et Personnalité) et chaque niveau (porte,
ligne, couleur, ton, base) : de combien de minutes l'heure de naissance peut avancer
(« before ») ou reculer (« after ») sans que la valeur change.

Méthode : une valeur change quand la longitude franchit un multiple de la largeur du
niveau (mêmes origine et sens que hd.chart.activation). On avance par pas prudents,
au plus la moitié du temps qu'il faudrait pour atteindre la frontière la plus proche
à la vitesse du moment (ce qui ne peut pas « sauter » une valeur, rétrogradation
comprise), puis on resserre par dichotomie à la demi-seconde.

Côté Design, décaler la naissance décale aussi le moment Design : la valeur est
recalculée au nouveau moment Design (88° d'arc solaire avant le nouveau Soleil).
"""
from datetime import timedelta

from . import data as D
from .ephemeris import design_jd, julian_day, lon_speed

LEVELS = {"gate": D.GATE_ARC, "line": D.LINE_ARC, "color": D.COLOR_ARC,
          "tone": D.TONE_ARC, "base": D.BASE_ARC}
HORIZON_MIN = 24 * 60          # au-delà : null (« plus de 24 h »)
MIN_STEP = 1 / 86400           # 1 s, en jours
MAX_STEP = 1 / 24              # 1 h, en jours
BISECT_TO = 0.5 / 86400        # 0,5 s

# Incertitude retenue pour chaque précision déclarée de l'heure (en minutes).
UNCERTAINTY_MINUTES = {"exacte": 5, "approximative": 60}


def _state(birth_jd: float, side: str, planet: str, t: float) -> tuple[float, float]:
    """Longitude et vitesse (°/jour de décalage de la naissance) pour une naissance décalée de t jours."""
    jd_b = birth_jd + t
    if side == "personality":
        return lon_speed(jd_b, planet)
    jd_d = design_jd(jd_b)
    lon, v = lon_speed(jd_d, planet)
    # d(moment Design)/d(naissance) = vitesse du Soleil à la naissance / au moment Design
    return lon, v * lon_speed(jd_b, "sun")[1] / lon_speed(jd_d, "sun")[1]


def _index(lon: float, arc: float) -> int:
    return int(((lon - D.WHEEL_START) % 360) // arc)


def next_change(birth_jd: float, side: str, planet: str, level: str, sign: int,
                start: float = 0.0, horizon: float = HORIZON_MIN / 1440) -> float | None:
    """Décalage (jours, signé) où la valeur change pour la première fois après `start`, ou None."""
    arc = LEVELS[level]
    lon, _ = _state(birth_jd, side, planet, start)
    v0 = _index(lon, arc)
    t = start
    while True:
        lon, rate = _state(birth_jd, side, planet, t)
        r = ((lon - D.WHEEL_START) % 360) % arc
        dist = min(r, arc - r)
        step = MAX_STEP if rate == 0 else min(MAX_STEP, max(MIN_STEP, 0.5 * dist / abs(rate)))
        nxt = t + sign * step
        if abs(nxt) > horizon:
            nxt = sign * horizon
        if _index(_state(birth_jd, side, planet, nxt)[0], arc) != v0:
            lo, hi = t, nxt
            while abs(hi - lo) > BISECT_TO:
                mid = (lo + hi) / 2
                if _index(_state(birth_jd, side, planet, mid)[0], arc) != v0:
                    hi = mid
                else:
                    lo = mid
            return hi
        if abs(nxt) >= horizon:
            return None
        t = nxt


def _minutes(t: float | None) -> float | None:
    return None if t is None else round(abs(t) * 1440, 1)


def stable_minutes(chart) -> dict:
    """{side: {planet: {level: {"before": min, "after": min}}}} — null : plus de 24 h."""
    jd = julian_day(chart.birth_utc)
    return {side: {p: {lvl: {"before": _minutes(next_change(jd, side, p, lvl, -1)),
                             "after": _minutes(next_change(jd, side, p, lvl, +1))}
                       for lvl in LEVELS}
                   for p in D.PLANETS}
            for side in ("design", "personality")}


def _core(chart) -> tuple:
    """Ce qui fait le thème : type, autorité, profil, définition, croix, canaux, centres."""
    return (chart.type, chart.authority, chart.profile, chart.definition, chart.cross,
            tuple(chart.channels), tuple(chart.defined_centers))


# Portes de tous les corps (canaux, centres, type, autorité, définition) et lignes
# du Soleil et de la Terre des deux côtés (profil, angle de la croix).
_CORE_VALUES = ([(s, p, "gate") for s in ("design", "personality") for p in D.PLANETS]
                + [(s, p, "line") for s in ("design", "personality") for p in ("sun", "earth")])


def chart_stable_minutes(chart, sign: int, horizon_min: float = HORIZON_MIN) -> float | None:
    """Minutes avant que le cœur du thème change (avance si sign = -1), ou None au-delà de l'horizon."""
    from .chart import build_chart
    jd, key0, horizon, t = julian_day(chart.birth_utc), _core(chart), horizon_min / 1440, 0.0
    while True:
        events = [e for e in (next_change(jd, *v, sign, start=t, horizon=horizon) for v in _CORE_VALUES)
                  if e is not None]
        if not events:
            return None
        t = min(events, key=abs)
        if _core(build_chart(chart.birth_utc + timedelta(days=t))) != key0:
            return _minutes(t)


VARIABLES = {  # flèche → (côté, corps)
    "determination": ("design", "sun"),
    "environment": ("design", "north_node"),
    "motivation": ("personality", "sun"),
    "perspective": ("personality", "north_node"),
}


def variables(chart) -> dict:
    """Les quatre flèches : direction (comme Chart.variables), et couleur, ton, base qui la portent."""
    keys = {"determination": "design_sun", "environment": "design_node",
            "motivation": "personality_sun", "perspective": "personality_node"}
    out = {}
    for name, (side, planet) in VARIABLES.items():
        a = getattr(chart, side)[planet]
        out[name] = {"side": side, "planet": planet, "direction": chart.variables[keys[name]],
                     "gate": a.gate, "line": a.line, "color": a.color, "tone": a.tone, "base": a.base}
    return out


def precision(chart, time_precision: str, stability: dict) -> dict:
    """Indicateur global : « fiable », « à confirmer » ou « incertain »."""
    w = UNCERTAINTY_MINUTES[time_precision]
    core = {"before": chart_stable_minutes(chart, -1), "after": chart_stable_minutes(chart, +1)}
    var = {k: min((stability[s][p]["tone"][k] for s, p in VARIABLES.values()),
                  key=lambda m: float("inf") if m is None else m)
           for k in ("before", "after")}
    shaky = lambda m: any(x is not None and x < w for x in m.values())
    if shaky(core):
        level = "incertain"
        note = f"À ±{w} min, le type, l'autorité, le profil, la croix ou les canaux peuvent changer."
    elif shaky(var):
        level = "à confirmer"
        note = f"À ±{w} min, le thème ne change pas, mais la couleur ou le ton d'une variable peut changer."
    else:
        level = "fiable"
        note = f"À ±{w} min, le thème et les variables ne changent pas (les bases peuvent changer)."
    return {"time_precision": time_precision, "uncertainty_minutes": w, "level": level,
            "chart_stable_minutes": core, "variables_stable_minutes": var, "note": note}
