# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Thèmes de test.

FICTIF_1 à FICTIF_5 : naissances FICTIVES (tirées au hasard, une par type). Leurs valeurs
sont celles que le moteur calcule aujourd'hui : ce sont des valeurs de NON-RÉGRESSION,
pas une vérification. La vérification contre les applis de référence (mybodygraph,
HumanDesignApp) se fait sur des naissances réelles, gardées hors du dépôt public dans
tests/references_privees.json (ignoré par git) : voir test_private_references_match_app.
"""
import json
from datetime import datetime
from pathlib import Path

import pytest

from hd.chart import build_chart
from hd.timeutil import local_to_utc

FICTIF_1 = dict(
    local=datetime(1985, 12, 12, 11, 45), tz="Europe/Paris",
    personality="26.4 45.4 11.4▲ 24.1 44.1 14.6 9.6 50.3 13.2 34.4 26.2▲ 10.5 28.5▲",
    design="47.6▼ 22.6 46.1 24.3 44.3 64.5 4.3▲ 59.4 19.1 43.5 5.4▲ 10.3 28.2",
    type="Generator", authority="Sacral", profile="4/6", definition=3,
    cross="Right Angle Cross of Rulership 4", channels=[(10, 34), (26, 44), (47, 64)],
    variables=("gauche", "droite", "gauche", "droite"),
    design_utc=datetime(1985, 9, 15, 6, 21),
)
FICTIF_2 = dict(
    local=datetime(1968, 2, 13, 18, 45), tz="America/New_York",
    personality="49.6 4.6 4.2▲ 51.6 57.6 30.4 61.2 36.6 59.2 17.6 46.1 14.3▼ 47.6",
    design="14.2 8.2▼ 45.4 3.2 50.2 28.6 48.1 54.6 59.5 17.3 46.1 43.6 47.6",
    type="Reflector", authority="Lunar", profile="6/2", definition=0,
    cross="Left Angle Cross of Revolution 1", channels=[],
    variables=("droite", "droite", "gauche", "gauche"),
    design_utc=datetime(1967, 11, 19, 9, 15),
)
FICTIF_3 = dict(
    local=datetime(1940, 7, 17, 19, 45), tz="Europe/Paris",
    personality="62.5 61.5 58.1▼ 48.6 21.6 31.1 12.5 33.2 24.5 2.1 8.1 6.1 31.1",
    design="3.1 50.1 7.5 57.6 51.6 25.2▲ 35.2▲ 16.5 42.3 27.2 23.2 6.1 56.5",
    type="Manifesting Generator", authority="Sacral", profile="5/1", definition=2,
    cross="Left Angle Cross of Obscuration 1",
    channels=[(7, 31), (16, 48), (24, 61), (25, 51), (27, 50)],
    variables=("droite", "gauche", "droite", "droite"),
    design_utc=datetime(1940, 4, 17, 3, 5),
)
FICTIF_4 = dict(
    local=datetime(1989, 1, 23, 16, 0), tz="Europe/Paris",
    personality="41.2 31.2 4.5 55.6 59.6 41.6 54.2 27.1▼ 8.2 58.5 10.6▼ 38.2 1.2",
    design="28.4 27.4▼ 12.1 63.2 64.2 57.3▲ 46.1 25.2▼ 20.5★ 10.1 11.6 58.5 44.5",
    type="Manifestor", authority="Splenic", profile="2/4", definition=2,
    cross="Right Angle Cross of the Unexpected 4",
    channels=[(1, 8), (4, 63), (10, 20), (10, 57), (20, 57), (28, 38)],
    variables=("gauche", "droite", "gauche", "droite"),
    design_utc=datetime(1988, 10, 28, 19, 28),
)
FICTIF_5 = dict(
    local=datetime(2008, 8, 5, 15, 15), tz="Europe/Paris",
    personality="7.1 13.1 18.3 13.6 7.6 4.2 29.6 47.5 38.6 40.3 22.6 49.5 10.1",
    design="2.3 1.3▼ 2.5 49.6▲ 4.6▲ 20.5 27.5 56.2 61.2 59.2 22.5 49.6▲ 10.3",
    type="Projector", authority="Self-Projected", profile="1/3", definition=1,
    cross="Right Angle Cross of the Sphinx 3", channels=[(10, 20)],
    variables=("gauche", "droite", "gauche", "droite"),
    design_utc=datetime(2008, 5, 5, 14, 59),
)
FICTIFS = [FICTIF_1, FICTIF_2, FICTIF_3, FICTIF_4, FICTIF_5]
PLANET_ORDER = ["sun", "earth", "moon", "north_node", "south_node", "mercury", "venus",
                "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]

PRIVATE = Path(__file__).with_name("references_privees.json")


def api_body(ref, **extra):
    """Le corps de /v1/chart pour un thème de test."""
    return {"date": ref["local"].strftime("%Y-%m-%d"), "time": ref["local"].strftime("%H:%M"),
            "time_precision": "exacte", "tz": ref["tz"], **extra}


def private_references():
    """Naissances réelles vérifiées sur mybodygraph (fichier local), ou [] si le fichier est absent."""
    if not PRIVATE.exists():
        return []
    refs = json.loads(PRIVATE.read_text(encoding="utf-8")).get("mybodygraph", [])
    for r in refs:
        r["local_dt"] = datetime.fromisoformat(r["local"])
    return refs


def check_chart(c, ref):
    assert " ".join(c.personality[p].label for p in PLANET_ORDER) == ref["personality"]
    assert " ".join(c.design[p].label for p in PLANET_ORDER) == ref["design"]
    assert c.type == ref["type"]
    assert c.authority == ref["authority"]
    assert c.profile == ref["profile"]
    assert c.definition == ref["definition"]
    assert c.cross == ref["cross"]
    assert [tuple(x) for x in c.channels] == [tuple(x) for x in ref["channels"]]
    v = c.variables
    assert (v["design_sun"], v["design_node"], v["personality_sun"], v["personality_node"]) == tuple(ref["variables"])


@pytest.mark.parametrize("ref", FICTIFS, ids=[f"fictif-{i}" for i in range(1, 6)])
def test_fictitious_charts_do_not_change(ref):
    c = build_chart(local_to_utc(ref["local"], ref["tz"]).utc)
    check_chart(c, ref)
    assert c.design_utc.replace(tzinfo=None, second=0, microsecond=0) == ref["design_utc"]


@pytest.mark.skipif(not PRIVATE.exists(), reason="tests/references_privees.json absent (fichier local, ignoré par git)")
def test_private_references_match_app():
    """Thèmes réels relevés sur mybodygraph.com (Jovian Archive), avec la fixation ▲▼★."""
    refs = private_references()
    assert refs
    for ref in refs:
        c = build_chart(local_to_utc(ref["local_dt"], ref["tz"]).utc)
        check_chart(c, ref)
        if "design_utc" in ref:
            assert c.design_utc.replace(tzinfo=None, second=0, microsecond=0) == datetime.fromisoformat(ref["design_utc"])
        if "active_gates_humandesignapp" in ref:  # capture HumanDesignApp : portes et côtés activés
            assert {str(g): sorted(s) for g, s in c.active_gates.items()} == \
                {g: sorted(s) for g, s in ref["active_gates_humandesignapp"].items()}
        if "cross_gates" in ref:
            assert c.cross_gates == ref["cross_gates"]
        if "defined_centers" in ref:
            assert c.defined_centers == ref["defined_centers"]


def test_timezone_history():
    assert local_to_utc(datetime(1997, 9, 12, 10, 0), "Europe/Paris").utc_offset_hours == 2
    assert local_to_utc(datetime(1966, 2, 10, 9, 0), "America/New_York").utc_offset_hours == -5
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
