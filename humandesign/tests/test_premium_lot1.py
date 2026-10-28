# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Lot 1 : couleur, ton, base, précision du moment Design, sensibilité à l'heure, variables.

Ces tests vérifient la cohérence du calcul (découpage, convergence, limites exactes).
Les valeurs à comparer à une appli de référence sont marquées « en attente de référence ».
"""
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import swisseph as swe

from hd import data as D
from hd import precision as P
from hd.chart import activation, build_chart
from hd.ephemeris import design_jd, julian_day
from hd.timeutil import local_to_utc

from .test_api import KEY, REFERENCE_1 as API_REF_1, call
from .test_reference import REFERENCE_1, REFERENCE_2, REFERENCE_3, REFERENCE_4, REFERENCE_5

REFS = [REFERENCE_1, REFERENCE_2, REFERENCE_3, REFERENCE_4, REFERENCE_5]
LEVEL_ORDER = ["base", "tone", "color", "line", "gate"]


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", KEY)


@pytest.fixture(scope="module")
def chart1():
    return build_chart(local_to_utc(REFERENCE_1["local"], REFERENCE_1["tz"]).utc)


@pytest.fixture(scope="module")
def stab1(chart1):
    return P.stable_minutes(chart1)


# ---------------------------------------------------------------- 1. découpage

def test_subdivisions_share_the_gate_origin_and_direction():
    """porte.ligne.couleur.ton.base désigne un intervalle de longitude qui contient la longitude."""
    rng = random.Random(1)
    for lon in [D.WHEEL_START, D.WHEEL_START - 1e-9, 0.0, 359.999999] + [rng.uniform(0, 360) for _ in range(2000)]:
        a = activation("sun", lon % 360)
        start = (D.WHEEL_START + D.GATE_ORDER.index(a.gate) * D.GATE_ARC + (a.line - 1) * D.LINE_ARC
                 + (a.color - 1) * D.COLOR_ARC + (a.tone - 1) * D.TONE_ARC + (a.base - 1) * D.BASE_ARC)
        offset = ((lon - start) % 360)
        assert offset < D.BASE_ARC + 1e-9, (lon, a)
        assert 1 <= a.line <= 6 and 1 <= a.color <= 6 and 1 <= a.tone <= 6 and 1 <= a.base <= 5


def test_first_base_of_gate_41_starts_at_the_wheel_origin():
    a = activation("sun", D.WHEEL_START + 1e-9)
    assert (a.gate, a.line, a.color, a.tone, a.base) == (41, 1, 1, 1, 1)
    b = activation("sun", D.WHEEL_START - 1e-9)
    assert (b.gate, b.line, b.color, b.tone, b.base) == (D.GATE_ORDER[-1], 6, 6, 6, 5)


# ---------------------------------------------------------------- 2. moment Design

@pytest.mark.parametrize("when", [ref["local"] for ref in REFS] + [
    datetime(1801, 6, 1, 12), datetime(1900, 1, 1), datetime(2000, 3, 20, 7, 35),
    datetime(2024, 12, 31, 23, 59), datetime(2399, 1, 1)])
def test_design_moment_is_precise_to_well_under_a_second(when):
    jd_b = julian_day(when.replace(tzinfo=timezone.utc))
    jd_d = design_jd(jd_b)
    sun_b = swe.calc_ut(jd_b, swe.SUN, swe.FLG_SWIEPH)[0][0]
    sun_d, _, _, speed = swe.calc_ut(jd_d, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SPEED)[0][:4]
    error_deg = abs(((sun_b - D.DESIGN_SOLAR_ARC - sun_d + 180) % 360) - 180)
    assert error_deg / speed * 86400 < 0.01  # en secondes de temps (exigé : < 1 s)
    assert 85 < jd_b - jd_d < 95


# ---------------------------------------------------------------- 3. sensibilité à l'heure

@pytest.mark.parametrize("side,planet,level", [
    ("personality", "moon", "base"), ("design", "moon", "base"), ("personality", "sun", "base"),
    ("design", "sun", "tone"), ("personality", "sun", "line"), ("design", "north_node", "tone"),
    ("personality", "earth", "color"), ("design", "mercury", "base")])
def test_stable_minutes_are_the_exact_limit(chart1, stab1, side, planet, level):
    """Juste avant la limite la valeur est la même ; juste après, elle a changé."""
    value = lambda dt: getattr(getattr(build_chart(chart1.birth_utc + timedelta(minutes=dt)), side)[planet], level)
    v0 = value(0)
    for direction, sign in (("before", -1), ("after", +1)):
        m = stab1[side][planet][level][direction]
        if m is None:
            continue
        if m > 0.1:
            assert value(sign * (m - 0.06)) == v0
        assert value(sign * (m + 0.06)) != v0


def test_coarser_levels_are_never_less_stable(stab1):
    inf = lambda m: math.inf if m is None else m
    for side in stab1.values():
        for levels in side.values():
            for d in ("before", "after"):
                seq = [inf(levels[lvl][d]) for lvl in LEVEL_ORDER]
                assert seq == sorted(seq)


def test_moon_base_changes_within_minutes_and_outer_gates_within_hours_do_not(stab1):
    moon = stab1["personality"]["moon"]["base"]
    assert min(moon["before"], moon["after"]) < 2
    assert stab1["personality"]["pluto"]["gate"] == {"before": None, "after": None}


def test_precision_levels_follow_declared_time_precision(chart1, stab1):
    exact = P.precision(chart1, "exacte", stab1)
    assert exact["level"] == "fiable" and exact["uncertainty_minutes"] == 5
    approx = P.precision(chart1, "approximative", stab1)
    assert approx["level"] in ("à confirmer", "incertain") and approx["uncertainty_minutes"] == 60
    core = exact["chart_stable_minutes"]
    assert core["before"] > 5 and core["after"] > 5


def test_chart_stability_is_where_the_chart_really_changes(chart1):
    m = P.chart_stable_minutes(chart1, +1)
    later = build_chart(chart1.birth_utc + timedelta(minutes=m + 0.06))
    same = build_chart(chart1.birth_utc + timedelta(minutes=m - 0.06))
    assert P._core(same) == P._core(chart1) != P._core(later)


# ---------------------------------------------------------------- 4. variables

def test_variables_reuse_the_existing_arrows(chart1):
    v = P.variables(chart1)
    assert set(v) == {"determination", "environment", "motivation", "perspective"}
    assert [v[k]["direction"] for k in ("determination", "environment", "motivation", "perspective")] == \
        list(REFERENCE_1["variables"])
    assert (v["determination"]["side"], v["determination"]["planet"]) == ("design", "sun")
    assert (v["perspective"]["side"], v["perspective"]["planet"]) == ("personality", "north_node")
    for x in v.values():
        assert x["direction"] == ("gauche" if x["tone"] <= 3 else "droite")


# ---------------------------------------------------------------- 5. API

def test_response_without_details_is_unchanged():
    code, r = call({**API_REF_1, "include_svg": False})
    assert code == 200
    assert not {"activations_details", "variables", "precision"} & set(r)


def test_details_option_adds_the_premium_fields():
    code, r = call({**API_REF_1, "include_svg": False, "details": True})
    assert code == 200
    sun = r["activations_details"]["design"]["sun"]
    assert set(sun) == {"gate", "line", "color", "tone", "base", "fixing", "label", "longitude", "stable_minutes"}
    assert set(sun["stable_minutes"]) == set(LEVEL_ORDER[::-1])
    assert set(r["activations_details"]["personality"]) == set(D.PLANETS)
    assert r["variables"]["determination"]["direction"] == r["details"]["variables"]["design_sun"]
    assert r["precision"]["level"] in ("fiable", "à confirmer", "incertain")


def test_details_must_be_a_boolean():
    code, r = call({**API_REF_1, "details": "oui"})
    assert code == 400 and r["error"]["code"] == "invalid_field"


# ---------------------------------------------------------------- en attente de référence

@pytest.mark.skip(reason="en attente de référence : couleur et ton des 13 corps × 2 côtés pour les 5 thèmes "
                         "de référence (les bases ne sont montrées par aucune appli : non vérifiées)")
def test_color_tone_base_match_reference_app():
    raise NotImplementedError


@pytest.mark.skip(reason="en attente de référence : couleur et ton des 4 variables pour les thèmes de référence "
                         "(directions vérifiées : référence 1 et référence privée B ; libellés à confirmer)")
def test_variables_match_reference_app():
    raise NotImplementedError


# ---------------------------------------------------------------- références privées (hors dépôt)

PRIVATE = Path(__file__).with_name("references_privees.json")


@pytest.mark.skipif(not PRIVATE.exists(), reason="tests/references_privees.json absent (fichier local, ignoré par git)")
def test_private_references():
    """Naissances de personnes réelles, gardées hors du dépôt public : mêmes valeurs que l'appli de référence."""
    for ref in json.loads(PRIVATE.read_text(encoding="utf-8"))["references"]:
        c = build_chart(local_to_utc(datetime.fromisoformat(ref["local"]), ref["tz"]).utc)
        assert f"{c.design['sun'].gate}.{c.design['sun'].line}" == ref["design_sun"], ref["nom"]
        assert f"{c.personality['sun'].gate}.{c.personality['sun'].line}" == ref["personality_sun"], ref["nom"]
        got = {k: v["direction"] for k, v in P.variables(c).items()}
        assert got == ref["variables"], ref["nom"]


# ---------------------------------------------------------------- bases : cohérence interne
# Aucune appli de référence ne montre les bases : ces tests vérifient seulement que le
# découpage est cohérent, pas qu'il correspond à une autre appli.

def test_every_base_of_the_wheel_follows_the_previous_one():
    """Les 69 120 bases du cercle, dans l'ordre : base, puis ton, couleur, ligne, porte basculent ensemble."""
    prev = None
    n = 64 * 6 * 6 * 6 * 5
    for i in range(n):
        a = activation("sun", (D.WHEEL_START + (i + 0.5) * D.BASE_ARC) % 360)
        cur = (D.GATE_ORDER.index(a.gate), a.line, a.color, a.tone, a.base)
        if prev is not None:
            g, l, c, t, b = prev
            b += 1
            if b > 5: b, t = 1, t + 1
            if t > 6: t, c = 1, c + 1
            if c > 6: c, l = 1, l + 1
            if l > 6: l, g = 1, g + 1
            assert cur == (g % 64, l, c, t, b), (i, prev, cur)
        prev = cur
    assert prev == (63, 6, 6, 6, 5)


@pytest.mark.parametrize("i", [0, 1, 4, 5, 29, 30, 179, 180, 1079, 1080, 69119])
def test_values_flip_exactly_at_the_base_boundary(i):
    edge = D.WHEEL_START + (i + 1) * D.BASE_ARC
    before, after = activation("sun", (edge - 1e-9) % 360), activation("sun", (edge + 1e-9) % 360)
    pick = lambda a: (a.gate, a.line, a.color, a.tone, a.base)
    assert pick(before) != pick(after)
    assert after.base == (before.base % 5) + 1
    assert (after.tone != before.tone) == (before.base == 5)


@pytest.mark.parametrize("side,planet", [("personality", "sun"), ("personality", "moon"), ("design", "sun")])
def test_base_window_matches_the_planet_speed(chart1, stab1, side, planet):
    """Durée d'une base (avant + après) ≈ largeur d'une base ÷ vitesse du corps à cet instant."""
    s = stab1[side][planet]["base"]
    _, rate = P._state(julian_day(chart1.birth_utc), side, planet, 0.0)
    expected = D.BASE_ARC / abs(rate) * 1440
    assert abs((s["before"] + s["after"]) - expected) < 0.05 * expected + 0.2
