# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Transits : les activations d'un instant (sans côté Design), leur superposition avec
un thème natal, et la vue d'une journée (heure exacte de chaque changement de porte et
de ligne).

Les heures de changement sont trouvées par recherche de racine sur la longitude (pas
bornés par la vitesse, puis dichotomie à la demi-seconde : hd.precision.next_change),
pas en testant chaque minute.
"""
import functools
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from . import data as D
from .chart import activation, analyse
from .ephemeris import julian_day, jd_to_datetime, positions
from .precision import next_change


def transit_activations(when_utc: datetime) -> dict:
    """{corps: Activation} à cet instant (porte, ligne, couleur, ton, base)."""
    pos = positions(julian_day(when_utc))
    return {p: activation(p, pos[p]) for p in D.PLANETS}


def overlay(natal, transit: dict) -> dict:
    """Ce que le transit ajoute au thème natal, le temps qu'il dure."""
    natal_gates = set(natal.active_gates)
    transit_gates = {a.gate for a in transit.values()}
    channels, defined, *_ = analyse(natal_gates | transit_gates)
    natal_channels = set(natal.channels)
    rows = []
    for x, y in channels:
        if (x, y) in natal_channels:
            continue
        n, t = sorted({x, y} & natal_gates), sorted({x, y} & transit_gates)
        rows.append({"channel": f"{x}-{y}", "natal_gates": n, "transit_gates": t,
                     # le transit a les deux portes : il forme le canal à lui seul
                     "kind": "transit" if len(t) == 2 else "completed"})
    return {
        # canaux que le transit complète avec une porte du thème
        "completed_channels": [r for r in rows if r["kind"] == "completed"],
        # canaux que le transit forme seul (ses deux portes)
        "transit_channels": [r["channel"] for r in rows if r["kind"] == "transit"],
        "temporarily_defined_centers": [c for c in defined if c not in natal.defined_centers],
        "defined_centers": defined,
    }


def _act(a) -> dict:
    return {"gate": a.gate, "line": a.line, "color": a.color, "tone": a.tone, "base": a.base,
            "label": f"{a.gate}.{a.line}", "longitude": round(a.longitude, 6)}


def transit(when_utc: datetime, natal=None) -> dict:
    acts = transit_activations(when_utc)
    out = {"at_utc": when_utc.astimezone(timezone.utc).isoformat(),
           "activations": {p: _act(a) for p, a in acts.items()}}
    if natal is not None:
        out["overlay"] = overlay(natal, acts)
    return out


def day_bounds(day, tz: str) -> tuple[datetime, datetime]:
    """Début et fin (UTC) de la journée locale : 23 h ou 25 h les jours de changement d'heure."""
    z = ZoneInfo(tz)
    start = datetime.combine(day, time(0), z).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time(0), z).astimezone(timezone.utc)
    return start, end


@functools.lru_cache(maxsize=64)  # aucune donnée personnelle : une journée calculée sert à tous
def day_changes(day, tz: str) -> dict:
    """Pour chaque corps : porte.ligne à 00:00, puis chaque changement de porte ou de ligne."""
    start, end = day_bounds(day, tz)
    jd0, length = julian_day(start), (end - start).total_seconds() / 86400
    z = ZoneInfo(tz)
    planets = {}
    for p in D.PLANETS:
        lon = positions(jd0)[p]
        a = activation(p, lon)
        cur, changes, t = (a.gate, a.line), [], 0.0
        while True:
            e = next_change(jd0, "personality", p, "line", +1, start=t, horizon=length)
            if e is None or e >= length:
                break
            b = activation(p, positions(jd0 + e)[p])
            moment = jd_to_datetime(jd0 + e)
            changes.append({
                "time": (moment + timedelta(seconds=30)).astimezone(z).strftime("%H:%M"),
                "utc": moment.replace(microsecond=0).isoformat(),
                "kind": "gate" if b.gate != cur[0] else "line",
                "from": f"{cur[0]}.{cur[1]}", "to": f"{b.gate}.{b.line}",
                "gate": b.gate, "line": b.line,
            })
            cur, t = (b.gate, b.line), e
        planets[p] = {"at_start": {"gate": a.gate, "line": a.line, "label": f"{a.gate}.{a.line}"},
                      "changes": changes}
    return {"date": day.isoformat(), "tz": tz, "start_utc": start.isoformat(), "end_utc": end.isoformat(),
            "planets": planets}
