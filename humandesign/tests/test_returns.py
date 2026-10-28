# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Lot 4 : retours solaire, de Saturne, de Chiron, opposition d'Uranus."""
from datetime import timedelta

import pytest

from hd.chart import build_chart
from hd.ephemeris import julian_day
from hd.returns import RETURNS, body_lon_speed, find_returns, years_with_returns
from hd.timeutil import local_to_utc

from .test_api import KEY, call
from .test_reference import REFERENCE_1, REFERENCE_2, REFERENCE_4

PERSON_1 = {"date": "1900-01-01", "time": "00:00", "time_precision": "exacte", "tz": "Europe/Paris"}


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", KEY)


def natal_of(ref):
    return build_chart(local_to_utc(ref["local"], ref["tz"]).utc)


def gap_deg(natal, kind, when):
    body, offset = RETURNS[kind]
    target = (body_lon_speed(julian_day(natal.birth_utc), body)[0] + offset) % 360
    return abs(((body_lon_speed(julian_day(when), body)[0] - target + 180) % 360) - 180)


@pytest.mark.parametrize("kind,year", [("solar", 2026), ("saturn", 2029), ("chiron", 2049), ("uranus_opposition", 2042)])
def test_each_passage_is_exact(kind, year):
    natal = natal_of(REFERENCE_1)
    passages = find_returns(natal, kind, year)
    assert passages
    for p in passages:
        assert gap_deg(natal, kind, p.when_utc) < 1e-5  # quelques centièmes de seconde de temps


def test_solar_return_once_a_year_near_the_birthday():
    natal = natal_of(REFERENCE_1)
    for year in (2000, 2026, 2100):
        (p,) = find_returns(natal, "solar", year)
        assert abs(p.when_utc.replace(year=1999) - natal.birth_utc) < timedelta(days=2)
        assert not p.retrograde


def test_retrograde_returns_give_all_three_passages():
    """Référence 2 : Saturne repasse trois fois en 1993 (direct, rétrograde, direct)."""
    natal = natal_of(REFERENCE_2)
    ps = find_returns(natal, "saturn", 1993)
    assert [p.retrograde for p in ps] == [False, True, False]
    assert 28 < ps[0].age_years < ps[-1].age_years < 31


def test_a_return_spanning_two_years_is_given_whole():
    """Référence 4 : l'opposition d'Uranus passe en 2041 puis deux fois en 2042."""
    natal = natal_of(REFERENCE_4)
    a, b = find_returns(natal, "uranus_opposition", 2041), find_returns(natal, "uranus_opposition", 2042)
    assert len(a) == 3 and [p.when_utc for p in a] == [p.when_utc for p in b]


@pytest.mark.parametrize("kind,ages", [("saturn", (27, 31)), ("chiron", (48, 52)), ("uranus_opposition", (38, 45))])
def test_returns_happen_at_the_expected_ages(kind, ages):
    for ref in (REFERENCE_1, REFERENCE_2, REFERENCE_4):
        natal = natal_of(ref)
        first = years_with_returns(natal, kind, 2399)[0]
        p = find_returns(natal, kind, first)[0]
        assert ages[0] <= p.age_years <= ages[1], (kind, ref["local"], p.age_years)


def test_no_return_in_the_months_after_birth():
    """Saturne rétrograde à la naissance repasse sur sa position : pas un retour."""
    natal = natal_of(REFERENCE_1)
    assert years_with_returns(natal, "saturn", 2399)[0] >= 2027
    assert find_returns(natal, "saturn", 2000) == []


def test_return_chart_follows_the_validated_design_rule():
    """Règle (a) : thème calculé comme une naissance au moment du retour (Design 88° de Soleil avant)."""
    natal = natal_of(REFERENCE_1)
    (p,) = find_returns(natal, "saturn", 2029)
    same = build_chart(p.when_utc)
    assert p.chart.design_utc == same.design_utc
    assert {k: (a.gate, a.line) for k, a in p.chart.design.items()} == {k: (a.gate, a.line) for k, a in same.design.items()}
    assert timedelta(days=85) < p.when_utc - p.chart.design_utc < timedelta(days=95)


# ---------------------------------------------------------------- API

def test_return_route():
    code, r = call({"chart": PERSON_1, "kind": "saturn", "year": 2029}, path="/v1/return")
    assert code == 200 and r["kind_fr"] == "retour de Saturne"
    (p,) = r["passages"]
    assert p["utc"].startswith("2029-05-22") and p["retrograde"] is False
    assert {"type", "profile", "cross", "channels", "details"} <= set(p["chart"])
    assert set(p["overlay"]) == {"completed_channels", "transit_channels", "temporarily_defined_centers", "defined_centers"}
    assert "years_with_returns" not in r


def test_a_year_without_return_points_to_the_right_years():
    code, r = call({"chart": PERSON_1, "kind": "saturn", "year": 2030}, path="/v1/return")
    assert code == 200 and r["passages"] == [] and 2029 in r["years_with_returns"]


@pytest.mark.parametrize("body", [
    {"chart": PERSON_1, "kind": "mars", "year": 2029},
    {"chart": PERSON_1, "kind": "saturn", "year": "2029"},
    {"chart": PERSON_1, "kind": "saturn", "year": True},
    {"chart": PERSON_1, "kind": "saturn", "year": 2399},
    {"chart": PERSON_1, "kind": "saturn", "year": 1999},
    {"kind": "saturn", "year": 2029},
    {"chart": {**PERSON_1, "skin": "atlas"}, "kind": "saturn", "year": 2029},
    {"chart": PERSON_1, "kind": "saturn", "year": 2029, "svg": True},
])
def test_return_input_errors(body):
    code, _ = call(body, path="/v1/return")
    assert code == 400


def test_return_requires_the_key():
    code, _ = call({"chart": PERSON_1, "kind": "solar", "year": 2026}, path="/v1/return", key=None)
    assert code == 401


# ---------------------------------------------------------------- en attente de référence

@pytest.mark.skip(reason="en attente de référence : date et heure d'un retour de Saturne (et du thème de retour) "
                         "relevées dans une appli de référence pour un thème de référence")
def test_returns_match_reference_app():
    raise NotImplementedError
