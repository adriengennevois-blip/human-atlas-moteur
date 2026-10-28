# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Retours : instants où une planète revient sur sa position natale (ou sur le point
opposé, pour l'opposition d'Uranus).

  solar              Soleil sur le Soleil natal (une fois par an)
  saturn             Saturne sur Saturne natal (vers 29 ans, puis vers 58 ans)
  chiron             Chiron sur Chiron natal (vers 50 ans)
  uranus_opposition  Uranus à l'opposé d'Uranus natal (vers 40 ans)

Une planète rétrograde peut repasser trois fois sur le même point : tous les passages
sont renvoyés, regroupés en un même retour quand ils sont rapprochés.

Thème de retour, règle validée : comme une naissance, au moment du passage. Le côté
Design est l'instant où le Soleil était 88° avant sa position au moment du retour.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

import swisseph as swe

from .chart import build_chart
from .ephemeris import FLAGS, jd_to_datetime, julian_day, lon_speed

RETURNS = {  # type → (corps, décalage par rapport à la position natale)
    "solar": ("sun", 0.0),
    "saturn": ("saturn", 0.0),
    "chiron": ("chiron", 0.0),
    "uranus_opposition": ("uranus", 180.0),
}
SCAN_DAYS = {"sun": 2.0, "saturn": 2.0, "chiron": 2.0, "uranus": 3.0}  # pas du balayage
SAME_RETURN_DAYS = 500   # passages plus rapprochés : un seul et même retour
TOLERANCE_DAYS = 1e-7    # ≈ 0,01 s
# Une planète lente, rétrograde à la naissance, repasse sur sa position dans les mois
# qui suivent : ce n'est pas un retour. On ne cherche qu'après la première année.
FIRST_DAYS_IGNORED = 300


def body_lon_speed(jd: float, body: str) -> tuple[float, float]:
    if body == "chiron":  # pas dans le thème : calculé à part (fichier seas_18.se1)
        xx, retflags = swe.calc_ut(jd, swe.CHIRON, FLAGS)
        if not retflags & swe.FLG_SWIEPH:
            raise RuntimeError("Swiss Ephemeris data files not found; set HD_EPHE_PATH")
        return xx[0], xx[3]
    return lon_speed(jd, body)


def _gap(jd: float, body: str, target: float) -> float:
    """Écart signé (°) entre la planète et le point visé, dans ]-180, 180]."""
    return ((body_lon_speed(jd, body)[0] - target + 180) % 360) - 180


def crossings(body: str, target: float, jd_from: float, jd_to: float) -> list[float]:
    """Tous les instants (jours juliens) où la planète passe sur `target` entre deux dates."""
    out, step = [], SCAN_DAYS[body]
    jd, g = jd_from, _gap(jd_from, body, target)
    while jd < jd_to:
        nxt = min(jd + step, jd_to)
        h = _gap(nxt, body, target)
        if g == 0:
            out.append(jd)
        elif g * h < 0 and abs(g) < 90 and abs(h) < 90:  # vrai passage, pas le saut à ±180°
            lo, hi = jd, nxt
            while hi - lo > TOLERANCE_DAYS:
                mid = (lo + hi) / 2
                if _gap(lo, body, target) * _gap(mid, body, target) <= 0:
                    hi = mid
                else:
                    lo = mid
            out.append((lo + hi) / 2)
        jd, g = nxt, h
    return out


def _groups(jds: list[float]) -> list[list[float]]:
    groups = []
    for jd in jds:
        if groups and jd - groups[-1][-1] < SAME_RETURN_DAYS:
            groups[-1].append(jd)
        else:
            groups.append([jd])
    return groups


@dataclass
class Passage:
    when_utc: datetime
    retrograde: bool
    age_years: float
    chart: object


def _jd_year(year: int) -> float:
    return swe.julday(year, 1, 1, 0.0, swe.GREG_CAL)


def find_returns(natal, kind: str, year: int) -> list[Passage]:
    """Passages du retour qui a lieu en `year` (tous ses passages, même s'ils débordent
    sur l'année voisine). Liste vide si aucun passage cette année-là."""
    body, offset = RETURNS[kind]
    jd_b = julian_day(natal.birth_utc)
    target = (body_lon_speed(jd_b, body)[0] + offset) % 360
    start, end = _jd_year(year), _jd_year(year + 1)
    found = crossings(body, target, max(_jd_year(year - 1), jd_b + FIRST_DAYS_IGNORED), _jd_year(year + 2))
    passages = []
    for group in _groups(found):
        if kind == "solar":
            group = [jd for jd in group if start <= jd < end]
        if not any(start <= jd < end for jd in group):
            continue
        for jd in group:
            passages.append(Passage(
                when_utc=jd_to_datetime(jd).astimezone(timezone.utc),
                retrograde=body_lon_speed(jd, body)[1] < 0,
                age_years=round((jd - jd_b) / 365.2425, 2),
                chart=build_chart(jd_to_datetime(jd)),
            ))
    return passages


def years_with_returns(natal, kind: str, until_year: int, max_age: int = 110) -> list[int]:
    """Années où ce retour a lieu dans une vie (pour orienter quand l'année demandée n'en a pas)."""
    body, offset = RETURNS[kind]
    jd_b = julian_day(natal.birth_utc)
    target = (body_lon_speed(jd_b, body)[0] + offset) % 360
    last = min(until_year, natal.birth_utc.year + max_age)
    groups = _groups(crossings(body, target, jd_b + FIRST_DAYS_IGNORED, _jd_year(last + 1)))
    return sorted({jd_to_datetime(jd).year for g in groups for jd in g})
