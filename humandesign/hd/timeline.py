# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Le transit posé sur une carte, dans le temps.

  transit_on_chart  un instant : positions (sens direct / rétrograde), portes, canaux et centres
                    que le transit active dans la carte
  person_intervals  sur un intervalle : quand un canal de la personne est complété par le transit,
                    quand un centre est défini par lui (heure de début et de fin)
  upcoming          « à venir » : le prochain événement notable dans les jours qui suivent

Ce qui est calculé ici ne dépend du temps que par les changements de PORTE des 13 corps
(hd.ingress, mis en cache pour tout le monde). Un canal est « complété » quand le transit porte
une porte du canal et la carte l'autre (même définition que hd.transit.overlay).
"""
from collections import Counter
from datetime import datetime, timedelta, timezone

from . import data as D
from .chart import activation, analyse
from .ephemeris import julian_day, lon_speed
from .ingress import events, iso
from .transit import _act, overlay, transit_activations

RESOLVE_DAYS = 120   # au-delà de la fenêtre, jusqu'où chercher la fin d'un événement qui la dépasse
MAX_UPCOMING_DAYS = 14


def transit_on_chart(natal, at: datetime) -> dict:
    """Le transit de l'instant « at » posé sur la carte « natal »."""
    acts = transit_activations(at)
    jd = julian_day(at.astimezone(timezone.utc))
    positions = {}
    for p in D.PLANETS:
        positions[p] = {**_act(acts[p]), "retrograde": lon_speed(jd, p)[1] < 0}
    ov = overlay(natal, acts)
    bodies = {}
    for p, a in acts.items():
        bodies.setdefault(a.gate, []).append(p)
    gates = [{"gate": g, "bodies": bodies[g], "in_natal": g in natal.active_gates,
              "natal_sides": natal.active_gates.get(g, [])} for g in sorted(bodies)]
    return {
        "at_utc": at.astimezone(timezone.utc).replace(microsecond=0).isoformat(),
        "positions": positions,
        "activates": {
            "gates": gates,
            "channels_completed": ov["completed_channels"],     # une porte du transit + une de la carte
            "channels_transit_only": ov["transit_channels"],    # les deux portes viennent du transit
            "centers_newly_defined": ov["temporarily_defined_centers"],
            "centers_defined": ov["defined_centers"],
        },
    }


# ---------------------------------------------------------------- intervalles

def _state(natal, transit_gates: set) -> tuple[dict, set]:
    """({canal: détail} complétés par le transit, centres nouvellement définis) pour ces portes."""
    natal_gates = set(natal.active_gates)
    channels, defined, *_ = analyse(natal_gates | transit_gates)
    own = set(natal.channels)
    completed = {}
    for x, y in channels:
        if (x, y) in own:
            continue
        t = sorted({x, y} & transit_gates)
        if len(t) == 1:  # une porte du transit, l'autre de la carte
            completed[f"{x}-{y}"] = {"natal_gates": sorted({x, y} & natal_gates), "transit_gates": t}
    return completed, {c for c in defined if c not in natal.defined_centers}


def _gate_events(start: datetime, end: datetime):
    """Changements de porte (pas de ligne) des 13 corps, regroupés par instant : [(jd, [(corps, de, vers)])]."""
    groups = []
    for e in events(start, end):
        if e["from"][0] == e["to"][0]:
            continue
        item = (e["planet"], e["from"][0], e["to"][0])
        if groups and abs(groups[-1][0] - e["jd"]) < 1e-9:
            groups[-1][1].append(item)
        else:
            groups.append((e["jd"], [item]))
    return groups


def person_intervals(natal, start: datetime, end: datetime, resolve_days: int = 0) -> list[dict]:
    """Les moments, sur ]début, fin], où le transit complète un canal de la carte ou y définit un centre.

    Chaque élément : kind « channel » ou « center », start_utc / end_utc (UTC, à la seconde).
    start_utc vaut null et started_before true si l'événement est déjà en cours au début ;
    end_utc vaut null et open_ended true s'il dure encore à la fin de la recherche (fin + resolve_days)."""
    scan_end = end + timedelta(days=resolve_days)
    jd0 = julian_day(start.astimezone(timezone.utc))
    gates = {p: activation(p, lon_speed(jd0, p)[0]).gate for p in D.PLANETS}
    counts = Counter(gates.values())
    completed, centers = _state(natal, set(counts))
    open_: dict = {}
    out: list[dict] = []

    def key_items(comp, cent):
        return {("channel", k): v for k, v in comp.items()} | {("center", c): {} for c in sorted(cent)}

    for key, detail in key_items(completed, centers).items():
        open_[key] = {"start": None, "detail": detail}
    for jd, changes in _gate_events(start, scan_end):
        for planet, g_from, g_to in changes:
            counts[g_from] -= 1
            if counts[g_from] <= 0:
                del counts[g_from]
            counts[g_to] += 1
        new = key_items(*_state(natal, set(counts)))
        for key in list(open_):
            if key not in new:
                out.append(_close(open_.pop(key), key, jd))
        for key, detail in new.items():
            if key not in open_:
                open_[key] = {"start": jd, "detail": detail}
    for key, rec in open_.items():
        out.append(_close(rec, key, None))
    jd_end = julian_day(end.astimezone(timezone.utc))
    out = [r for r in out if r["_start"] is None or r["_start"] <= jd_end]
    out.sort(key=lambda r: (-1e18 if r["_start"] is None else r["_start"], r["kind"] != "channel"))
    for r in out:
        del r["_start"], r["_end"]
    return out


def _close(rec: dict, key: tuple, jd_end) -> dict:
    kind, name = key
    out = {"kind": kind, **({"channel": name, **rec["detail"]} if kind == "channel" else {"center": name}),
           "start_utc": None if rec["start"] is None else iso(rec["start"]),
           "end_utc": None if jd_end is None else iso(jd_end),
           "started_before": rec["start"] is None, "open_ended": jd_end is None,
           "_start": rec["start"], "_end": jd_end}
    if rec["start"] is not None and jd_end is not None:
        out["duration_hours"] = round((jd_end - rec["start"]) * 24, 1)
    return out


def upcoming(natal, at: datetime, days: int = 7) -> dict:
    """Le prochain événement notable (canal complété, centre défini) dans les « days » jours."""
    end = at + timedelta(days=days)
    rows = person_intervals(natal, at, end, resolve_days=RESOLVE_DAYS)
    current = [r for r in rows if r["started_before"]]
    coming = [r for r in rows if not r["started_before"]]
    first = lambda kind: next((r for r in coming if r["kind"] == kind), None)
    return {
        "at_utc": at.astimezone(timezone.utc).replace(microsecond=0).isoformat(),
        "window_end_utc": end.astimezone(timezone.utc).replace(microsecond=0).isoformat(),
        "days": days,
        "next": coming[0] if coming else None,
        "next_channel": first("channel"),
        "next_center": first("center"),
        "upcoming": coming,
        "current": current,
    }
