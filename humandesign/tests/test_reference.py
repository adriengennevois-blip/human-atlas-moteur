# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

from datetime import datetime

import pytest

from hd.chart import build_chart
from hd.timeutil import local_to_utc

# Reference values taken from mybodygraph.com (Jovian Archive), incl. line fixing ▲▼★.
REFERENCE_1 = dict(
    local=datetime(1999, 9, 20, 8, 26), tz="Europe/Paris",
    personality="6.5▼ 36.5 61.4▲ 33.5 19.5 18.3 4.2 9.6▼ 27.2 2.4 13.1 60.6 9.3",
    design="15.1 10.1 6.6 7.1▲ 13.1 62.3 7.1▲ 32.6 3.3 24.6 13.4 41.2 9.4▼",
    type="Generator", authority="Sacral", profile="5/1", definition=3,
    cross="Left Angle Cross of the Plane 2", channels=[(3, 60), (13, 33), (24, 61)],
    variables=("droite", "droite", "gauche", "droite"),
)
REFERENCE_2 = dict(
    local=datetime(1964, 2, 5, 5, 15), tz="America/New_York",
    personality="13.3 7.3 1.2 39.2 38.2 61.2 36.1 13.6▲ 51.1 49.6▼ 40.4▲ 1.5 64.3▼",
    design="1.5 2.5▼ 64.6 39.4 38.4 43.3 9.1 5.1▲ 21.2 13.4 40.4▲ 1.3 64.3▼",
    type="Reflector", authority="Lunar", profile="3/5", definition=0,
    cross="Right Angle Cross of the Sphinx 1", channels=[],
    variables=("gauche", "gauche", "gauche", "gauche"),
    design_utc=datetime(1963, 11, 10, 18, 37),
)
REFERENCE_3 = dict(
    local=datetime(1942, 5, 24, 16, 30), tz="Europe/Paris",
    personality="20.3★ 34.3▲ 47.1 40.4 37.4 12.2▼ 51.6 53.3▼ 12.4▼ 20.3★ 20.1 6.5 31.2",
    design="55.5▼ 59.5 35.4▲ 64.3▼ 63.3 19.5 41.4▼ 23.5 35.1 23.4 8.3 46.1▲ 31.3",
    type="Manifesting Generator", authority="Emotional", profile="3/5", definition=2,
    cross="Right Angle Cross of the Sleeping Phoenix 2",
    channels=[(6, 59), (20, 34), (37, 40), (47, 64)],
    variables=("droite", "gauche", "droite", "droite"),
    design_utc=datetime(1942, 2, 24, 0, 37),
)
REFERENCE_4 = dict(
    local=datetime(1998, 3, 9, 9, 10), tz="Europe/Paris",
    personality="22.2▲ 47.2 31.5▼ 40.6 37.6 25.4 41.2 25.6 37.3▲ 51.5▼ 19.4 60.6 9.3",
    design="26.4 45.4 20.1▼ 64.4 63.4 10.4▼ 60.5▲ 61.6▼ 13.6 21.5 41.5▼ 60.3 9.1▲",
    type="Manifestor", authority="Emotional", profile="2/4", definition=2,
    cross="Right Angle Cross of Rulership 1",
    channels=[(10, 20), (21, 45), (25, 51), (37, 40), (47, 64)],
    variables=("droite", "gauche", "droite", "droite"),
    design_utc=datetime(1997, 12, 12, 13, 15),
)
REFERENCE_5 = dict(
    local=datetime(2002, 3, 28, 16, 50), tz="Europe/Paris",
    personality="17.5 18.5 18.3 45.5 26.5 36.6 42.6 23.1▼ 52.4▼ 16.5 30.3 19.3 26.1",
    design="38.1 39.1 62.3 12.5 11.5 61.5 58.3 63.6 39.2▼ 16.4 49.4 41.6 5.5▼",
    type="Projector", authority="Emotional", profile="5/1", definition=2,
    cross="Left Angle Cross of Upheaval 1",
    channels=[(17, 62), (18, 58), (19, 49), (30, 41)],
    variables=("droite", "gauche", "gauche", "gauche"),
)
PLANET_ORDER = ["sun", "earth", "moon", "north_node", "south_node", "mercury", "venus",
                "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]


@pytest.mark.parametrize("ref", [REFERENCE_1, REFERENCE_2, REFERENCE_3, REFERENCE_4, REFERENCE_5],
                         ids=["reference-1", "reference-2", "reference-3", "reference-4", "reference-5"])
def test_reference_chart(ref):
    c = build_chart(local_to_utc(ref["local"], ref["tz"]).utc)
    assert " ".join(c.personality[p].label for p in PLANET_ORDER) == ref["personality"]
    assert " ".join(c.design[p].label for p in PLANET_ORDER) == ref["design"]
    assert c.type == ref["type"]
    assert c.authority == ref["authority"]
    assert c.profile == ref["profile"]
    assert c.definition == ref["definition"]
    assert c.cross == ref["cross"]
    assert c.channels == ref["channels"]
    v = c.variables
    assert (v["design_sun"], v["design_node"], v["personality_sun"], v["personality_node"]) == ref["variables"]
    if "design_utc" in ref:
        assert c.design_utc.replace(tzinfo=None, second=0, microsecond=0) == ref["design_utc"]


def test_timezone_history():
    assert local_to_utc(datetime(1999, 9, 20, 8, 26), "Europe/Paris").utc_offset_hours == 2
    assert local_to_utc(datetime(1964, 2, 5, 5, 15), "America/New_York").utc_offset_hours == -5
    # France under German occupation: UTC+2 even in winter
    assert local_to_utc(datetime(1942, 1, 15, 12, 0), "Europe/Paris").utc_offset_hours == 2
    # France had no DST between 1946 and 1975
    assert local_to_utc(datetime(1970, 7, 1, 12, 0), "Europe/Paris").utc_offset_hours == 1


def test_dst_edge_warnings():
    gap = local_to_utc(datetime(2021, 3, 28, 2, 30), "Europe/Paris")
    assert gap.warning and "inexistante" in gap.warning
    amb = local_to_utc(datetime(2021, 10, 31, 2, 30), "Europe/Paris", fold=1)
    assert amb.warning and "ambiguë" in amb.warning
    assert amb.utc_offset_hours == 1
