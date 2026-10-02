# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

import os
from datetime import datetime, timedelta, timezone

import swisseph as swe

from .data import DESIGN_SOLAR_ARC

EPHE_PATH = os.environ.get("HD_EPHE_PATH", os.path.join(os.path.dirname(__file__), "..", "ephe"))
swe.set_ephe_path(os.path.abspath(EPHE_PATH))

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

SWE_BODIES = {
    "sun": swe.SUN, "moon": swe.MOON, "north_node": swe.TRUE_NODE,
    "mercury": swe.MERCURY, "venus": swe.VENUS, "mars": swe.MARS,
    "jupiter": swe.JUPITER, "saturn": swe.SATURN, "uranus": swe.URANUS,
    "neptune": swe.NEPTUNE, "pluto": swe.PLUTO,
}


def julian_day(dt_utc: datetime) -> float:
    h = dt_utc.hour + dt_utc.minute / 60 + (dt_utc.second + dt_utc.microsecond / 1e6) / 3600
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, h, swe.GREG_CAL)


def jd_to_datetime(jd: float) -> datetime:
    y, m, d, h = swe.revjul(jd, swe.GREG_CAL)
    return datetime(y, m, d, tzinfo=timezone.utc) + timedelta(hours=h)


def _lon(jd: float, body: int) -> float:
    xx, retflags = swe.calc_ut(jd, body, FLAGS)
    if not retflags & swe.FLG_SWIEPH:
        raise RuntimeError("Swiss Ephemeris data files not found; set HD_EPHE_PATH")
    return xx[0]


def positions(jd: float) -> dict:
    out = {name: _lon(jd, body) for name, body in SWE_BODIES.items()}
    out["earth"] = (out["sun"] + 180.0) % 360
    out["south_node"] = (out["north_node"] + 180.0) % 360
    return out


def design_jd(birth_jd: float) -> float:
    """Moment the Sun stood exactly 88° of solar arc before its birth position."""
    target = (_lon(birth_jd, swe.SUN) - DESIGN_SOLAR_ARC) % 360
    jd = birth_jd - 89.0
    for _ in range(100):
        diff = ((target - _lon(jd, swe.SUN) + 180) % 360) - 180
        if abs(diff) < 1e-10:
            break
        speed = swe.calc_ut(jd, swe.SUN, FLAGS)[0][3]
        jd += diff / speed
    return jd
