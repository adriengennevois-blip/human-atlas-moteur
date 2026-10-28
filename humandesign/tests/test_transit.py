# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Lot 3 : transits d'un instant, superposition avec un thème, vue du jour."""
from datetime import date, datetime, timedelta, timezone

import pytest

from hd import data as D
from hd.chart import activation, build_chart
from hd.ephemeris import julian_day, positions
from hd.timeutil import local_to_utc
from hd.transit import day_bounds, day_changes, overlay, transit, transit_activations

from .test_api import KEY, call
from .test_reference import FICTIF_1, api_body

AT = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
PERSON_1 = api_body(FICTIF_1)


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", KEY)


@pytest.fixture(scope="module")
def natal():
    return build_chart(local_to_utc(FICTIF_1["local"], FICTIF_1["tz"]).utc)


def value(p, when):
    a = activation(p, positions(julian_day(when))[p])
    return a.gate, a.line


# ---------------------------------------------------------------- transit d'un instant

def test_transit_is_the_personality_side_of_that_instant():
    acts = transit_activations(AT)
    same = build_chart(AT).personality
    assert set(acts) == set(D.PLANETS)
    for p in D.PLANETS:
        a, b = acts[p], same[p]
        assert (a.gate, a.line, a.color, a.tone, a.base) == (b.gate, b.line, b.color, b.tone, b.base)


def test_overlay_adds_only_what_the_transit_brings(natal):
    acts = transit_activations(AT)
    o = overlay(natal, acts)
    natal_gates, transit_gates = set(natal.active_gates), {a.gate for a in acts.values()}
    own = {f"{x}-{y}" for x, y in natal.channels}
    for r in o["completed_channels"]:
        x, y = map(int, r["channel"].split("-"))
        assert r["channel"] not in own and (x, y) in D.CHANNELS
        assert r["natal_gates"] and r["transit_gates"]
        assert {x, y} <= set(r["natal_gates"]) | set(r["transit_gates"])
        assert set(r["natal_gates"]) <= natal_gates and set(r["transit_gates"]) <= transit_gates
    for ch in o["transit_channels"]:
        x, y = map(int, ch.split("-"))
        assert {x, y} <= transit_gates and ch not in own
    for r in o["completed_channels"]:
        assert len(r["transit_gates"]) == 1  # sinon le transit forme le canal seul
    assert not set(o["temporarily_defined_centers"]) & set(natal.defined_centers)
    assert set(natal.defined_centers) <= set(o["defined_centers"])


def _at_gate(gate):
    lon = (D.WHEEL_START + D.GATE_ORDER.index(gate) * D.GATE_ARC + D.GATE_ARC / 2) % 360
    return activation("moon", lon)


def test_overlay_synthetic_cases():
    """Thème avec la seule porte 24 : un transit en 61 complète 24-61 (Tête et Ajna définies le temps du transit).
    Thème sans ces portes : un transit en 24 et en 61 forme le canal seul."""
    from types import SimpleNamespace
    natal = SimpleNamespace(active_gates={24: ["design"]}, channels=[], defined_centers=[])
    o = overlay(natal, {"moon": _at_gate(61)})
    assert o["completed_channels"] == [{"channel": "24-61", "natal_gates": [24], "transit_gates": [61], "kind": "completed"}]
    assert o["transit_channels"] == [] and o["temporarily_defined_centers"] == ["head", "ajna"]
    empty = SimpleNamespace(active_gates={}, channels=[], defined_centers=[])
    o = overlay(empty, {"moon": _at_gate(61), "sun": _at_gate(24)})
    assert o["completed_channels"] == [] and o["transit_channels"] == ["24-61"]


# ---------------------------------------------------------------- vue du jour

def test_day_is_23_or_25_hours_when_the_clock_changes():
    s, e = day_bounds(date(2026, 3, 29), "Europe/Paris")
    assert e - s == timedelta(hours=23)
    s, e = day_bounds(date(2026, 10, 25), "Europe/Paris")
    assert e - s == timedelta(hours=25)


@pytest.fixture(scope="module")
def day():
    return day_changes(date(2026, 10, 28), "Europe/Paris")


def test_each_change_happens_at_the_announced_minute(day):
    for p, v in day["planets"].items():
        prev = v["at_start"]["label"]
        for c in v["changes"]:
            t = datetime.fromisoformat(c["utc"])
            before, after = value(p, t - timedelta(seconds=30)), value(p, t + timedelta(seconds=30))
            assert f"{before[0]}.{before[1]}" == c["from"] == prev and f"{after[0]}.{after[1]}" == c["to"]
            assert c["kind"] == ("gate" if before[0] != after[0] else "line")
            prev = c["to"]


def test_no_change_is_missed(day):
    """Contrôle minute par minute (test seulement : le moteur, lui, cherche la racine)."""
    start, end = (datetime.fromisoformat(day[k]) for k in ("start_utc", "end_utc"))
    for p, v in day["planets"].items():
        seen, t, last = 0, start, value(p, start)
        while t < end:
            t += timedelta(minutes=1)
            cur = value(p, min(t, end - timedelta(seconds=1)))
            if cur != last:
                seen += 1
                last = cur
        assert seen == len(v["changes"]), p


def test_moon_changes_line_many_times_a_day_and_the_sun_about_once(day):
    assert 12 <= len(day["planets"]["moon"]["changes"]) <= 20
    assert len(day["planets"]["sun"]["changes"]) <= 2


# ---------------------------------------------------------------- API

def test_transit_route_now_and_at_a_given_instant(natal):
    code, r = call({}, path="/v1/transit")
    assert code == 200 and abs(datetime.fromisoformat(r["at_utc"]) - datetime.now(timezone.utc)) < timedelta(minutes=1)
    assert "overlay" not in r and set(r["activations"]) == set(D.PLANETS)
    code, r = call({"at": "2026-10-28T13:00:00+01:00", "chart": PERSON_1}, path="/v1/transit")
    assert code == 200 and r["at_utc"].startswith("2026-10-28T12:00:00")
    assert r["natal"]["type"] == "Generator"
    assert r["overlay"] == overlay(natal, transit_activations(AT))


@pytest.mark.parametrize("body", [
    {"at": "2026-10-28T12:00:00"}, {"at": "demain"}, {"at": "1700-01-01T00:00:00Z"}, {"at": 12},
    {"chart": {**PERSON_1, "include_svg": True}}, {"quand": "maintenant"}])
def test_transit_input_errors(body):
    code, r = call(body, path="/v1/transit")
    assert code == 400


def test_transit_natal_errors_are_labelled():
    code, r = call({"chart": {**PERSON_1, "time_precision": "inconnue"}}, path="/v1/transit")
    assert code == 422 and r["error"]["message"].startswith("thème natal :")


def test_day_route(day):
    code, r = call(None, method="GET", path="/v1/transits/day", raw=b"",
                   headers={"QUERY_STRING": "date=2026-10-28&tz=Europe/Paris"})
    assert code == 200 and r == day


@pytest.mark.parametrize("qs", ["", "date=28/10/2026", "date=2026-02-30", "date=2026-10-28&tz=Paris",
                                "date=2026-10-28&x=1", "date=1700-01-01"])
def test_day_route_errors(qs):
    code, _ = call(None, method="GET", path="/v1/transits/day", raw=b"", headers={"QUERY_STRING": qs})
    assert code == 400


def test_day_route_needs_the_key_and_get():
    code, _ = call(None, method="GET", path="/v1/transits/day", raw=b"", key=None,
                   headers={"QUERY_STRING": "date=2026-10-28"})
    assert code == 401
    code, _ = call({}, path="/v1/transits/day")
    assert code == 405


TRANSITS_KEY = "t" * 40


def test_transits_key_opens_only_the_day_view(monkeypatch):
    monkeypatch.setenv("TRANSITS_API_KEY", TRANSITS_KEY)
    day = lambda key: call(None, method="GET", path="/v1/transits/day", raw=b"", key=key,
                           headers={"QUERY_STRING": "date=2026-10-28"})[0]
    assert day(TRANSITS_KEY) == 200 and day(KEY) == 200
    for path, body in (("/v1/chart", PERSON_1), ("/v1/transit", {}), ("/v1/composite", {"people": [PERSON_1, PERSON_1]})):
        assert call(body, path=path, key=TRANSITS_KEY)[0] == 401


@pytest.mark.parametrize("short", ["", "court"])
def test_short_transits_key_opens_nothing(monkeypatch, short):
    monkeypatch.setenv("TRANSITS_API_KEY", short)
    code, _ = call(None, method="GET", path="/v1/transits/day", raw=b"", key=short or "x",
                   headers={"QUERY_STRING": "date=2026-10-28"})
    assert code == 401


def test_transit_requires_the_key():
    code, _ = call({}, path="/v1/transit", key=None)
    assert code == 401


# ---------------------------------------------------------------- référence HumanDesignApp

# « Current Transits », HumanDesignApp 5.8.7, 28 octobre 2026 à 21:48 (heure de Paris).
HDA_2026_10_28 = {"sun": "28.4", "earth": "27.4", "moon": "35.1", "north_node": "30.3▲", "south_node": "29.3",
                  "mercury": "43.1", "venus": "50.2▼", "mars": "7.5", "jupiter": "4.6", "saturn": "17.6",
                  "uranus": "20.5▼", "neptune": "25.5", "pluto": "41.2"}


def test_transits_match_humandesignapp():
    r = transit(datetime(2026, 10, 28, 20, 48, tzinfo=timezone.utc))
    assert {p: a["label"] for p, a in r["activations"].items()} == HDA_2026_10_28
    assert r["channels"] == ["27-50", "30-41"]                      # Preservation, Recognition
    assert set(r["defined_centers"]) == {"spleen", "sacral", "solar_plexus", "root"}


@pytest.mark.skip(reason="en attente de référence : heures de changement de porte et de ligne d'une journée "
                         "relevées dans une appli de référence (curseur de la vue « 24 hours »)")
def test_day_view_matches_reference_app():
    raise NotImplementedError
