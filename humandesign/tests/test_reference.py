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
    local=datetime(1900, 1, 1), tz="Europe/Paris",
    personality="SUPPRIME",
    design="SUPPRIME",
    type="Generator", authority="Sacral", profile="5/1", definition=3,
    cross="Left Angle Cross of the Plane 2", channels=[(3, 60), (13, 33), (24, 61)],
    variables=("droite", "droite", "gauche", "droite"),
)
REFERENCE_2 = dict(
    local=datetime(1900, 1, 1), tz="America/New_York",
    personality="SUPPRIME",
    design="SUPPRIME",
    type="Reflector", authority="Lunar", profile="3/5", definition=0,
    cross="Right Angle Cross of the Sphinx 1", channels=[],
    variables=("gauche", "gauche", "gauche", "gauche"),
    design_utc=datetime(1900, 1, 1),
)
REFERENCE_3 = dict(
    local=datetime(1900, 1, 1), tz="Europe/Paris",
    personality="SUPPRIME",
    design="SUPPRIME",
    type="Manifesting Generator", authority="Emotional", profile="3/5", definition=2,
    cross="Right Angle Cross of the Sleeping Phoenix 2",
    channels=[(6, 59), (20, 34), (37, 40), (47, 64)],
    variables=("droite", "gauche", "droite", "droite"),
    design_utc=datetime(1900, 1, 1),
)
REFERENCE_4 = dict(
    local=datetime(1900, 1, 1), tz="Europe/Paris",
    personality="SUPPRIME",
    design="SUPPRIME",
    type="Manifestor", authority="Emotional", profile="2/4", definition=2,
    cross="Right Angle Cross of Rulership 1",
    channels=[(10, 20), (21, 45), (25, 51), (37, 40), (47, 64)],
    variables=("droite", "gauche", "droite", "droite"),
    design_utc=datetime(1900, 1, 1),
)
REFERENCE_5 = dict(
    local=datetime(1900, 1, 1), tz="Europe/Paris",
    personality="SUPPRIME",
    design="SUPPRIME",
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
    assert local_to_utc(datetime(1900, 1, 1), "Europe/Paris").utc_offset_hours == 2
    assert local_to_utc(datetime(1900, 1, 1), "America/New_York").utc_offset_hours == -5
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
