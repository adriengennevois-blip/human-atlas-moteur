# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Lot 5 : groupes de 3 à 5 personnes (la Penta attend ses règles)."""
from types import SimpleNamespace

import pytest

from hd.chart import analyse, build_chart
from hd.composite import composite
from hd.group import group
from hd.timeutil import local_to_utc

from .test_api import KEY, call
from .test_reference import REFERENCE_1, REFERENCE_2, REFERENCE_3, REFERENCE_4, REFERENCE_5

REFS = [REFERENCE_1, REFERENCE_2, REFERENCE_3, REFERENCE_4, REFERENCE_5]
PEOPLE = [
    {"date": "1900-01-01", "time": "00:00", "time_precision": "exacte", "tz": "Europe/Paris", "name": "Référence 1"},
    {"date": "1900-01-01", "time": "00:00", "time_precision": "exacte", "tz": "America/New_York", "name": "Référence 2"},
    {"date": "1900-01-01", "time": "00:00", "time_precision": "exacte", "tz": "Europe/Paris", "name": "Référence 3"},
    {"date": "1900-01-01", "time": "00:00", "time_precision": "exacte", "tz": "Europe/Paris", "name": "Référence 4"},
    {"date": "1900-01-01", "time": "00:00", "time_precision": "exacte", "tz": "Europe/Paris", "name": "Référence 5"},
]


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", KEY)


@pytest.fixture(scope="module")
def charts():
    return [build_chart(local_to_utc(r["local"], r["tz"]).utc) for r in REFS]


def fake(*gates):
    return SimpleNamespace(active_gates={g: ["design"] for g in gates}, channels=[], defined_centers=[])


def test_who_brings_what_on_a_built_case():
    """24-61 : 1 et 2 apportent la 24, 3 la 61 ; personne n'a le canal seul."""
    g = group([fake(24), fake(24), fake(61)])
    (row,) = [r for r in g["channels"] if r["channel"] == "24-61"]
    assert row == {"channel": "24-61", "gates": {"24": [1, 2], "61": [3]}, "holders": [], "only_together": True}
    assert g["channels_only_together"] == ["24-61"] and g["centers_only_together"] == ["head", "ajna"]


def test_holders_are_people_with_the_whole_channel():
    g = group([fake(24, 61), fake(61), fake(3)])
    (row,) = [r for r in g["channels"] if r["channel"] == "24-61"]
    assert row["holders"] == [1] and not row["only_together"] and row["gates"] == {"24": [1], "61": [1, 2]}


@pytest.mark.parametrize("n", [3, 4, 5])
def test_group_is_the_union_of_everyone(charts, n):
    cs = charts[:n]
    g = group(cs)
    channels, defined, *_ = analyse(set().union(*(set(c.active_gates) for c in cs)))
    assert [r["channel"] for r in g["channels"]] == [f"{x}-{y}" for x, y in channels]
    assert g["defined_centers"] == defined and g["size"] == n
    for r in g["channels"]:
        for gate, people in r["gates"].items():
            assert people == [i for i, c in enumerate(cs, 1) if int(gate) in c.active_gates]


def test_pairs_reuse_the_composite(charts):
    cs = charts[:4]
    g = group(cs)
    assert [p["people"] for p in g["pairs"]] == [[1, 2], [1, 3], [1, 4], [2, 3], [2, 4], [3, 4]]
    p = g["pairs"][4]  # personnes 2 et 4
    assert {k: v for k, v in p.items() if k != "people"} == composite(cs[1], cs[3])


def test_penta_waits_for_its_rules(charts):
    assert group(charts[:5])["penta"]["status"] == "pending_rules"


# ---------------------------------------------------------------- API

def test_group_route():
    code, r = call({"people": PEOPLE}, path="/v1/group")
    assert code == 200 and set(r) == {"people", "group"}
    assert [p["name"] for p in r["people"]] == [p["name"] for p in PEOPLE]
    assert len(r["group"]["pairs"]) == 10 and r["group"]["penta"]["status"] == "pending_rules"


@pytest.mark.parametrize("n", [0, 2, 6])
def test_group_size_is_limited(n):
    code, r = call({"people": (PEOPLE * 2)[:n]}, path="/v1/group")
    assert code == 400 and "de 3 à 5" in r["error"]["message"]


def test_group_errors_say_which_person():
    people = PEOPLE[:2] + [{**PEOPLE[2], "time_precision": "inconnue"}]
    code, r = call({"people": people}, path="/v1/group")
    assert code == 422 and r["error"]["message"].startswith("personne 3 :")
    code, r = call({"people": PEOPLE[:2] + [{**PEOPLE[2], "skin": "atlas"}]}, path="/v1/group")
    assert code == 400


def test_group_requires_the_key():
    code, _ = call({"people": PEOPLE[:3]}, path="/v1/group", key=None)
    assert code == 401
