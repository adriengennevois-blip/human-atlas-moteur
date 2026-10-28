# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Lot 2 : composite de deux personnes."""
import re
from pathlib import Path
from xml.etree import ElementTree

import pytest

from hd import data as D
from hd.bodygraph import EXTRA_SKINS, PAGE_W, SKINS
from hd.chart import analyse, build_chart
from hd.composite import composite, composite_active_gates, connection, render_composite
from hd.timeutil import local_to_utc

from .test_api import KEY, call
from .test_reference import FICTIF_1, FICTIF_4, api_body

PERSON_1 = api_body(FICTIF_1, name="Fictif 1")
PERSON_4 = api_body(FICTIF_4, name="Fictif 4")


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", KEY)


@pytest.fixture(scope="module")
def charts():
    return [build_chart(local_to_utc(r["local"], r["tz"]).utc) for r in (FICTIF_1, FICTIF_4)]


# ---------------------------------------------------------------- les quatre connexions

@pytest.mark.parametrize("a,b,kind,holder", [
    ({24}, {61}, "electromagnetic", None),        # chacun une porte
    ({24, 61}, {61}, "compromise", "a"),          # canal complet / une seule porte
    ({24}, {24, 61}, "compromise", "b"),
    ({24, 61}, set(), "dominance", "a"),          # canal complet / aucune porte
    ({3}, {24, 61}, "dominance", "b"),
    ({24, 61}, {24, 61}, "companionship", None),  # tous les deux le canal complet
])
def test_connection_kinds(a, b, kind, holder):
    r = connection((24, 61), a, b)
    assert (r["connection"], r["holder"], r["channel"]) == (kind, holder, "24-61")
    assert r["gates"] == {"a": sorted(a & {24, 61}), "b": sorted(b & {24, 61})}


def test_same_gate_on_both_sides_is_not_a_channel():
    channels, *_ = analyse({24} | {24})
    assert (24, 61) not in channels


def test_swapping_the_two_people_mirrors_the_result(charts):
    ab, ba = composite(*charts), composite(*reversed(charts))
    assert [r["channel"] for r in ab["channels"]] == [r["channel"] for r in ba["channels"]]
    flip = {"a": "b", "b": "a", None: None}
    for x, y in zip(ab["channels"], ba["channels"]):
        assert x["connection"] == y["connection"] and flip[x["holder"]] == y["holder"]
        assert x["gates"] == {"a": y["gates"]["b"], "b": y["gates"]["a"]}
    assert {k: v for k, v in ab.items() if k != "channels"} == {k: v for k, v in ba.items() if k != "channels"}


# ---------------------------------------------------------------- la composite de deux thèmes

def test_composite_is_the_union_of_both_charts(charts):
    a, b = charts
    c = composite(a, b)
    union = set(a.active_gates) | set(b.active_gates)
    channels, defined, ctype, _, definition = analyse(union)
    assert [r["channel"] for r in c["channels"]] == [f"{x}-{y}" for x, y in channels]
    assert (c["defined_centers"], c["type"], c["definition"]) == (defined, ctype, definition)
    assert c["type_fr"] == D.TYPES_FR[ctype][0]


def test_each_person_s_own_channels_are_held(charts):
    a, b = charts
    rows = {r["channel"]: r for r in composite(a, b)["channels"]}
    for who, chart in (("a", a), ("b", b)):
        for x, y in chart.channels:
            r = rows[f"{x}-{y}"]
            assert r["connection"] == "companionship" or r["holder"] == who


def test_channels_only_together_are_the_electromagnetic_ones(charts):
    a, b = charts
    c = composite(a, b)
    own = {f"{x}-{y}" for ch in (a, b) for x, y in ch.channels}
    assert set(c["channels_only_together"]) == {r["channel"] for r in c["channels"]} - own
    assert c["channels_only_together"]  # ces deux thèmes en ont (12-22, 20-34, 27-50, 34-57)
    assert set(c["centers_only_together"]) <= set(c["defined_centers"])
    assert not set(c["centers_only_together"]) & (set(a.defined_centers) | set(b.defined_centers))


# ---------------------------------------------------------------- carte SVG

def test_composite_card(charts):
    svg = render_composite(*charts, "Léa", "Tom & <Zoé>", uid="cmp")
    ElementTree.fromstring(svg)
    s = EXTRA_SKINS["composite"]
    assert "Léa" in svg and "Tom &amp; &lt;Zoé&gt;" in svg
    assert s["design"] in svg and s["personality"] in svg
    assert "Personnalité</text>" not in svg  # pas de colonnes de planètes
    ids = re.findall(r'\bid="([^"]+)"', svg)
    assert len(ids) == len(set(ids)) and all(i.startswith("cmp-") for i in ids)
    assert set(re.findall(r'url\(#([^)]+)\)', svg)) <= set(ids)


def test_composite_skin_is_not_offered_for_a_single_chart():
    assert "composite" not in SKINS
    code, r = call({**PERSON_1, "skin": "composite"})
    assert code == 400


def test_composite_gate_colors_follow_each_person(charts):
    a, b = charts
    gates = composite_active_gates(a, b)
    assert set(gates) == set(a.active_gates) | set(b.active_gates)
    both = set(a.active_gates) & set(b.active_gates)
    assert all(gates[g] == ["design", "personality"] for g in both)


def test_two_long_first_names_fit(charts):
    ttLib = pytest.importorskip("fontTools.ttLib")
    pytest.importorskip("brotli")
    f = ttLib.TTFont(Path(__file__).parents[1] / "hd" / "fonts" / "instrument-serif-italic.woff2")
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    a, b = "Marie-Gwendolyne Ölü", "Maximilien-Édouard B"
    svg = render_composite(*charts, a, b)
    size = float(re.search(r'font-style="italic" font-size="([\d.]+)" text-anchor="middle"><tspan', svg).group(1))
    width = sum(hmtx[cmap[ord(ch)]][0] for ch in f"{a} & {b}") / upm * size
    assert width <= PAGE_W - 40


# ---------------------------------------------------------------- API

def test_composite_route():
    code, r = call({"people": [PERSON_1, PERSON_4]}, path="/v1/composite")
    assert code == 200
    assert set(r) == {"people", "composite", "svg"}
    assert [p["name"] for p in r["people"]] == ["Fictif 1", "Fictif 4"]
    assert r["people"][0]["type"] == "Generator" and r["people"][1]["type"] == "Manifestor"
    assert {x["connection"] for x in r["composite"]["channels"]} <= {
        "electromagnetic", "compromise", "dominance", "companionship"}
    ElementTree.fromstring(r["svg"])


def test_composite_without_svg():
    code, r = call({"people": [PERSON_1, PERSON_4], "include_svg": False}, path="/v1/composite")
    assert code == 200 and "svg" not in r


@pytest.mark.parametrize("body,code_", [
    ({"people": [PERSON_1]}, "invalid_field"),
    ({"people": [PERSON_1, PERSON_4, PERSON_1]}, "invalid_field"),
    ({"people": "deux"}, "invalid_field"),
    ({"people": [PERSON_1, PERSON_4], "skin": "atlas"}, "unknown_field"),
    ({"people": [PERSON_1, {**PERSON_4, "include_svg": False}]}, "unknown_field"),
    ({"people": [PERSON_1, PERSON_4], "include_svg": "oui"}, "invalid_field"),
])
def test_composite_input_errors(body, code_):
    code, r = call(body, path="/v1/composite")
    assert code == 400 and r["error"]["code"] == code_


def test_composite_person_errors_say_which_person():
    code, r = call({"people": [PERSON_1, {**PERSON_4, "time_precision": "inconnue"}]}, path="/v1/composite")
    assert code == 422 and r["error"]["message"].startswith("personne 2 :")


def test_composite_requires_the_key():
    code, _ = call({"people": [PERSON_1, PERSON_4]}, path="/v1/composite", key=None)
    assert code == 401


# ---------------------------------------------------------------- en attente de référence

@pytest.mark.skip(reason="en attente de référence : composite de deux thèmes réels "
                         "(type de connexion de chaque canal) relevée dans une appli de référence")
def test_composite_matches_reference_app():
    raise NotImplementedError
