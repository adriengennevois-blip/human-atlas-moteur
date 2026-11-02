# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Espace premium : ingressions (frise), transit posé sur une carte, « à venir », fiche de lecture.

Les ingressions sont vérifiées contre les éphémérides elles-mêmes (la Lune à une seconde avant puis
après l'instant annoncé) et contre la vue du jour existante (hd.transit.day_changes).
"""
import re
import time
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from xml.etree import ElementTree

import pytest

from hd import data as D
from hd import ingress as I
from hd import reading_fr as R
from hd import variables_fr as VF
from hd.bodygraph import render_bodygraph
from hd.chart import activation, build_chart
from hd.ephemeris import julian_day, lon_speed, positions
from hd.reading import reading
from hd.themes import THEMES
from hd.timeline import person_intervals, transit_on_chart, upcoming
from hd.timeutil import local_to_utc
from hd.transit import day_changes, overlay, transit_activations

from .test_api import KEY, call
from .test_reference import FICTIF_1, api_body

UTC = timezone.utc
START = datetime(2026, 10, 28, tzinfo=UTC)
PERSON = api_body(FICTIF_1)


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", KEY)


@pytest.fixture(scope="module")
def natal():
    return build_chart(local_to_utc(FICTIF_1["local"], FICTIF_1["tz"]).utc)


def at(dt):
    return activation("moon", lon_speed(julian_day(dt), "moon")[0])


# ---------------------------------------------------------------- ingressions

def test_a_moon_gate_change_is_verifiable_against_the_ephemeris():
    """À la seconde annoncée, la Lune change de porte : une seconde avant, l'ancienne ; une seconde après, la nouvelle."""
    r = I.ingresses(START, START + timedelta(days=3), level="gate")
    changes = r["planets"]["moon"]["changes"]
    assert len(changes) >= 6  # ≈ 2,3 portes par jour
    for c in changes[:6]:
        when = datetime.fromisoformat(c["utc"])
        before, after = at(when - timedelta(seconds=2)), at(when + timedelta(seconds=2))
        assert f"{before.gate}.{before.line}" == c["from"] and f"{after.gate}.{after.line}" == c["to"], c
        assert before.gate != after.gate and c["kind"] == "gate" and c["gate"] == after.gate


def test_every_line_change_of_every_body_is_exact_to_the_minute():
    """Pour les 13 corps : 30 s avant l'heure annoncée, l'ancienne ligne ; 30 s après, la nouvelle."""
    r = I.ingresses(START, START + timedelta(days=2))
    for planet, v in r["planets"].items():
        if planet in ("sun", "moon", "earth"):
            assert v["changes"], planet  # les corps rapides changent de ligne au moins une fois en 2 jours
        for c in v["changes"]:
            when = datetime.fromisoformat(c["utc"])
            b = activation(planet, positions(julian_day(when - timedelta(seconds=30)))[planet])
            a = activation(planet, positions(julian_day(when + timedelta(seconds=30)))[planet])
            assert (f"{b.gate}.{b.line}", f"{a.gate}.{a.line}") == (c["from"], c["to"]), (planet, c)


@pytest.mark.parametrize("day", [date(2026, 10, 28), date(2026, 3, 29), date(2025, 6, 1), date(2024, 2, 29)])
def test_same_changes_as_the_existing_day_view(day):
    st = datetime(day.year, day.month, day.day, tzinfo=UTC)
    mine = I.ingresses(st, st + timedelta(days=1))
    ref = day_changes(day, "UTC")
    for p, v in ref["planets"].items():
        a, b = mine["planets"][p]["changes"], v["changes"]
        assert [c["to"] for c in a] == [c["to"] for c in b], (day, p)
        for x, y in zip(a, b):
            assert abs((datetime.fromisoformat(x["utc"]) - datetime.fromisoformat(y["utc"])).total_seconds()) <= 1.5


def test_windows_are_assembled_without_gap_or_duplicate():
    r = I.ingresses(START, START + timedelta(days=40))
    for p, v in r["planets"].items():
        cur = v["at_start"]["label"]
        times = []
        for c in v["changes"]:
            assert c["from"] == cur, (p, c)  # chaque changement part de l'état où le précédent a fini
            cur = c["to"]
            times.append(c["utc"])
        assert times == sorted(times) and len(set(times)) == len(times)
    # deux fenêtres qui se recouvrent donnent les mêmes changements
    r2 = I.ingresses(START + timedelta(days=10), START + timedelta(days=30))
    inside = lambda res: [c["utc"] for c in res["planets"]["moon"]["changes"]
                          if START + timedelta(days=10) < datetime.fromisoformat(c["utc"]) <= START + timedelta(days=30)]
    assert inside(r) == [c["utc"] for c in r2["planets"]["moon"]["changes"]]


def test_earth_and_south_node_change_with_the_sun_and_north_node():
    r = I.ingresses(START, START + timedelta(days=60))["planets"]
    assert [c["utc"] for c in r["earth"]["changes"]] == [c["utc"] for c in r["sun"]["changes"]]
    assert [c["utc"] for c in r["south_node"]["changes"]] == [c["utc"] for c in r["north_node"]["changes"]]


def test_retrograde_flag_is_the_sign_of_the_speed():
    r = I.ingresses(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 12, 31, tzinfo=UTC))
    seen = set()
    for p in ("mercury", "venus", "mars", "jupiter", "saturn", "north_node"):
        for c in r["planets"][p]["changes"]:
            when = datetime.fromisoformat(c["utc"])
            assert c["retrograde"] == (lon_speed(julian_day(when), p)[1] < 0), (p, c)
            seen.add(c["retrograde"])
    assert seen == {True, False}  # le test a bien rencontré des changements en rétrogradation


def test_a_year_and_28_days_are_fast_and_cached():
    I.clear_cache()
    t = time.perf_counter()
    r = I.ingresses(START, START + timedelta(days=28))
    assert time.perf_counter() - t < 2 and r["count"] > 300
    I.clear_cache()
    t = time.perf_counter()
    year = I.ingresses(START, START + timedelta(days=365))
    cold = time.perf_counter() - t
    assert cold < 2 and year["count"] > 6000
    hits = I._day.cache_info().hits
    t = time.perf_counter()
    I.ingresses(START + timedelta(days=3), START + timedelta(days=360))  # fenêtre voisine : jours en cache
    assert I._day.cache_info().hits > hits and time.perf_counter() - t < cold


def test_ingress_input_errors():
    with pytest.raises(ValueError):
        I.ingresses(START, START)
    with pytest.raises(ValueError):
        I.ingresses(START, START + timedelta(days=367))
    with pytest.raises(ValueError):
        I.ingresses(datetime(2026, 1, 1), datetime(2026, 1, 2, tzinfo=UTC))


# ---------------------------------------------------------------- transit posé sur la carte

AT = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def test_transit_on_chart_positions_and_activations(natal):
    r = transit_on_chart(natal, AT)
    assert list(r["positions"]) == D.PLANETS
    acts = transit_activations(AT)
    jd = julian_day(AT)
    for p, x in r["positions"].items():
        assert (x["gate"], x["line"], x["color"], x["tone"], x["base"]) == (acts[p].gate, acts[p].line, acts[p].color, acts[p].tone, acts[p].base)
        assert x["retrograde"] == (lon_speed(jd, p)[1] < 0)
    ov = overlay(natal, acts)
    a = r["activates"]
    assert a["channels_completed"] == ov["completed_channels"] and a["channels_transit_only"] == ov["transit_channels"]
    assert a["centers_newly_defined"] == ov["temporarily_defined_centers"]
    assert {g["gate"] for g in a["gates"]} == {x.gate for x in acts.values()}
    for g in a["gates"]:
        assert g["in_natal"] == (g["gate"] in natal.active_gates)


def test_transit_route_with_svg_for_both_themes():
    renders = {}
    for theme in ("atlas", "gdh"):
        code, r = call({"chart": PERSON, "at": "2026-11-02T12:00:00Z", "theme": theme, "show_variables": True}, path="/v1/transit/chart")
        assert code == 200 and set(r) == {"natal", "at_utc", "positions", "activates", "svg"}
        ElementTree.fromstring(r["svg"])
        gates = {g["gate"] for g in r["activates"]["gates"]}
        assert {int(n) for n in re.findall(r'class="transit-ring-(\d+)"', r["svg"])} == gates
        for center in r["activates"]["centers_newly_defined"]:
            assert f'class="transit-center-{center}"' in r["svg"]
        assert "transit du 02/11/2026 à 12:00 UTC" in r["svg"]
        assert THEMES[theme]["transit"] in r["svg"]
        renders[theme] = r["svg"]
    # gdh hérite d'atlas : même structure, seules les couleurs diffèrent (aux identifiants près)
    def colorless(svg):
        svg = re.sub(r"hd[0-9a-f]{8}", "UID", svg)                       # identifiant tiré au hasard
        svg = re.sub(r"#[0-9a-fA-F]{6}\b", "#", svg)                      # valeurs de couleur
        svg = re.sub(r'(?<=id=")gdh-|(?<=url\(#)gdh-', "", svg)            # préfixe des identifiants de gdh
        return re.sub(r">(orange|violet|or|bleu nuit)</tspan>", ">c</tspan>", svg)  # nom des couleurs, dans la légende

    assert colorless(renders["atlas"]) == colorless(renders["gdh"])
    assert THEMES["gdh"]["transit"] == THEMES["atlas"]["transit"]  # gdh hérite d'atlas


def test_transit_route_json_only_and_defaults():
    code, r = call({"chart": PERSON, "at": "2026-11-02T12:00:00Z", "include_svg": False}, path="/v1/transit/chart")
    assert code == 200 and "svg" not in r
    code, r = call({"chart": PERSON}, path="/v1/transit/chart")  # sans « at » : maintenant
    assert code == 200 and "svg" in r and r["at_utc"].startswith(str(datetime.now(UTC).year))
    assert "transit-ring" not in render_bodygraph(build_chart(local_to_utc(datetime(2000, 1, 1, 12), "Europe/Paris").utc), uid="u")


@pytest.mark.parametrize("body", [
    {}, {"chart": None}, {"chart": PERSON, "at": "pas une date"}, {"chart": PERSON, "at": "2026-11-02T12:00:00"},
    {"chart": PERSON, "theme": "classique"}, {"chart": PERSON, "include_svg": "oui"}, {"chart": PERSON, "x": 1},
    {"chart": {**PERSON, "show_variables": True}}, {"chart": {**PERSON, "time_precision": "inconnue"}},
])
def test_transit_route_errors(body):
    code, r = call(body, path="/v1/transit/chart")
    assert code in (400, 422) and "error" in r


# ---------------------------------------------------------------- canaux complétés dans le temps

def _completed(natal, when):
    return {r["channel"] for r in overlay(natal, transit_activations(when))["completed_channels"]}


def test_person_intervals_agree_with_the_overlay_minute_by_minute(natal):
    """Toutes les 25 minutes pendant 4 jours : les canaux complétés et centres définis donnés par les
    intervalles sont ceux de l'overlay calculé directement à cet instant."""
    start, end = AT, AT + timedelta(days=4)
    rows = person_intervals(natal, start, end, resolve_days=30)
    edges = [datetime.fromisoformat(x[k]) for x in rows for k in ("start_utc", "end_utc") if x[k]]
    t = start
    while t < end:
        if min((abs((t - e).total_seconds()) for e in edges), default=1e9) > 120:  # pas au bord d'un intervalle
            from_rows = {r["channel"] for r in rows if r["kind"] == "channel" and _active(r, t)}
            assert from_rows == _completed(natal, t), t
            centers = {r["center"] for r in rows if r["kind"] == "center" and _active(r, t)}
            assert centers == set(overlay(natal, transit_activations(t))["temporarily_defined_centers"]), t
        t += timedelta(minutes=25)


def _active(r, t):
    s = datetime.fromisoformat(r["start_utc"]) if r["start_utc"] else None
    e = datetime.fromisoformat(r["end_utc"]) if r["end_utc"] else None
    return (s is None or s <= t) and (e is None or t < e)


def test_each_interval_starts_and_ends_at_the_announced_instant(natal):
    rows = [r for r in person_intervals(natal, AT, AT + timedelta(days=5), resolve_days=30)
            if r["kind"] == "channel" and not r["started_before"] and not r["open_ended"]]
    assert len(rows) >= 3
    for r in rows:
        s, e = datetime.fromisoformat(r["start_utc"]), datetime.fromisoformat(r["end_utc"])
        assert r["channel"] not in _completed(natal, s - timedelta(minutes=1))
        assert r["channel"] in _completed(natal, s + timedelta(minutes=1))
        assert r["channel"] in _completed(natal, e - timedelta(minutes=1))
        assert r["channel"] not in _completed(natal, e + timedelta(minutes=1))
        assert r["duration_hours"] == pytest.approx((e - s).total_seconds() / 3600, abs=0.1)


def test_upcoming_gives_the_next_event_with_start_and_end(natal):
    u = upcoming(natal, AT)
    assert u["days"] == 7 and u["next"] is not None
    start = datetime.fromisoformat(u["next"]["start_utc"])
    assert AT < start <= AT + timedelta(days=7)
    assert datetime.fromisoformat(u["next"]["end_utc"]) > start
    assert u["next"]["start_utc"] == min(r["start_utc"] for r in u["upcoming"])  # le tout premier
    assert u["next_channel"]["kind"] == "channel"
    assert u["next_center"] is None or u["next_center"]["kind"] == "center"
    firsts = [x for x in (u["next_channel"], u["next_center"]) if x]
    assert u["next"]["start_utc"] == min(x["start_utc"] for x in firsts)
    # centres : Gorge, Plexus solaire et Racine sont définis par le transit en continu pour cette carte
    # (confirmé par échantillonnage), donc déjà « en cours » et sans nouveau début dans la semaine
    assert {r["center"] for r in u["current"] if r["kind"] == "center"} == {"throat", "solar_plexus", "root"}
    assert {r["channel"] for r in u["current"] if r["kind"] == "channel"} == _completed(natal, AT)
    assert all(not r["started_before"] for r in u["upcoming"])


def test_upcoming_and_ingresses_routes(natal):
    code, r = call({"chart": PERSON, "at": "2026-11-02T12:00:00Z"}, path="/v1/upcoming")
    assert code == 200 and r["next"]["kind"] in ("channel", "center") and r["natal"]["type"] == natal.type
    assert r["next"] == upcoming(natal, AT)["next"]
    code, r = call({"chart": PERSON, "at": "2026-11-02T12:00:00Z", "days": 14}, path="/v1/upcoming")
    assert code == 200 and r["days"] == 14
    code, r = call({"from": "2026-11-02T00:00:00Z", "to": "2026-11-09T00:00:00Z", "chart": PERSON}, path="/v1/ingresses")
    assert code == 200 and r["count"] > 100 and set(r["planets"]) == set(D.PLANETS)
    assert r["person_events"] == person_intervals(natal, datetime(2026, 11, 2, tzinfo=UTC), datetime(2026, 11, 9, tzinfo=UTC))
    code, r = call({"from": "2026-11-02T00:00:00Z", "to": "2026-11-09T00:00:00Z", "level": "gate"}, path="/v1/ingresses")
    assert code == 200 and "person_events" not in r
    assert all(c["kind"] == "gate" for v in r["planets"].values() for c in v["changes"])
    # la naissance envoyée n'est jamais renvoyée en clair
    for path, body in (("/v1/upcoming", {"chart": PERSON, "at": "2026-11-02T12:00:00Z"}),
                       ("/v1/transit/chart", {"chart": PERSON, "include_svg": False}),
                       ("/v1/ingresses", {"from": "2026-11-02T00:00:00Z", "to": "2026-11-09T00:00:00Z", "chart": PERSON})):
        text = str(call(body, path=path)[1])
        assert "1985-12-12" not in text and "11:45" not in text, path


@pytest.mark.parametrize("path,body", [
    ("/v1/ingresses", {}), ("/v1/ingresses", {"from": "2026-11-02T00:00:00Z"}),
    ("/v1/ingresses", {"from": "2026-11-09T00:00:00Z", "to": "2026-11-02T00:00:00Z"}),
    ("/v1/ingresses", {"from": "2026-01-01T00:00:00Z", "to": "2027-01-03T00:00:00Z"}),   # 367 jours
    ("/v1/ingresses", {"from": "2026-11-02T00:00:00", "to": "2026-11-09T00:00:00Z"}),    # sans fuseau
    ("/v1/ingresses", {"from": "2026-11-02T00:00:00Z", "to": "2026-11-09T00:00:00Z", "level": "ligne"}),
    ("/v1/upcoming", {}), ("/v1/upcoming", {"chart": PERSON, "days": 0}), ("/v1/upcoming", {"chart": PERSON, "days": 15}),
    ("/v1/upcoming", {"chart": PERSON, "days": True}),
])
def test_premium_input_errors(path, body):
    code, r = call(body, path=path)
    assert code == 400 and "error" in r


def test_one_year_is_accepted_and_fast_enough():
    I.clear_cache()
    t = time.perf_counter()
    code, r = call({"from": "2026-11-02T00:00:00Z", "to": "2027-11-02T00:00:00Z"}, path="/v1/ingresses")
    assert code == 200 and r["count"] > 6000 and time.perf_counter() - t < 2


# ---------------------------------------------------------------- fiche de lecture

def test_reading_is_off_by_default_and_on_request():
    code, r = call({**PERSON, "include_svg": False})
    assert code == 200 and "reading" not in r
    code, r = call({**PERSON, "include_svg": False, "reading": True})
    assert code == 200 and r["reading"]["version"] == 1
    code, r = call({**PERSON, "reading": "oui"})
    assert code == 400 and r["error"]["code"] == "invalid_field"
    code, _ = call({"people": [PERSON, {**PERSON, "reading": True}]}, path="/v1/composite")
    assert code == 400


def test_reading_entries_have_stable_ids(natal):
    r = reading(natal)
    ids = [e["id"] for e in r["entries"]]
    assert len(ids) == len(set(ids))
    expected = ["channels", "type", "strategy", "authority", "profile", "definition", "cross", "signature",
                "not_self_theme", "centers.defined", "centers.open"]
    for v in ("digestion", "environment", "motivation", "perspective"):
        expected += [f"{v}.orientation", f"{v}.color", f"{v}.tone"] + ([f"{v}.subcategory"] if v in ("digestion", "environment") else []) + [f"{v}.base"]
    expected += ["relations.me_vs_others", "sleep.rhythm"]
    assert ids == expected
    assert all(e["section"] in R.SECTION_NAMES_FR for e in r["entries"])


def test_reading_data_matches_the_chart(natal):
    e = {x["id"]: x for x in reading(natal)["entries"]}
    assert [c["channel"] for c in e["channels"]["value"]["channels"]] == [f"{a}-{b}" for a, b in natal.channels]
    assert e["channels"]["value"]["count"] == len(natal.channels)
    assert e["type"]["value"] == {"key": "Generator", "name": "Générateur"}
    assert e["strategy"]["value"]["name"] == "Répondre" and e["signature"]["value"]["name"] == "Satisfaction"
    assert e["not_self_theme"]["value"]["name"] == "Frustration"
    assert e["profile"]["value"]["key"] == "4/6" and (e["profile"]["value"]["personality_line"], e["profile"]["value"]["design_line"]) == (4, 6)
    assert e["definition"]["value"] == {"number": 3, "name": "Triple split"}
    assert e["cross"]["value"]["name"] == natal.cross and e["cross"]["value"]["angle"]["key"] == "right-angle"
    assert e["cross"]["value"]["gates"] == {"personality_sun": 26, "personality_earth": 45, "design_sun": 47, "design_earth": 22}
    defined = [c["key"] for c in e["centers.defined"]["value"]]
    opened = [c["key"] for c in e["centers.open"]["value"]]
    assert defined == [c for c in D.CENTERS if c in natal.defined_centers] and set(defined) | set(opened) == set(D.CENTERS) and not set(defined) & set(opened)


def test_reading_variables_follow_the_classic_correspondences(natal):
    """Digestion : couleur → nom ; ton → direct/indirect…, comme les tables validées (variables_fr)."""
    e = {x["id"]: x["value"] for x in reading(natal)["entries"]}
    # fictif 1 : Digestion couleur 5 « Son », ton 2 → gauche, sous-catégorie du côté gauche « Aigu »
    assert e["digestion.orientation"]["key"] == "left" and e["digestion.orientation"]["name"] == "gauche"
    assert e["digestion.color"] == {"number": 5, "name": {"fr": "Son", "en": "Sound"}}
    assert e["digestion.tone"]["number"] == 2 and e["digestion.subcategory"]["name"]["fr"] == "Aigu"
    assert e["digestion.base"] == {"number": 4}
    assert e["environment.color"]["name"]["fr"] == "Montagnes" and e["environment.subcategory"]["name"]["fr"] == "Passif"
    assert e["environment.orientation"]["key"] == "right"
    assert e["perspective.color"]["name"]["fr"] == "Personnel" and e["perspective.color"]["opposite_name"]["fr"] == "Pouvoir"
    assert e["motivation.color"]["name"]["fr"] == "Besoin"
    assert "motivation.subcategory" not in e and "perspective.subcategory" not in e  # pas de sous-catégorie
    # le ton décide du côté du sous-libellé : tons 1 à 3 → premier nom du couple, tons 4 à 6 → second
    from .test_reference import FICTIFS
    sides = set()
    for ref in FICTIFS:
        c = build_chart(local_to_utc(ref["local"], ref["tz"]).utc)
        entries = {x["id"]: x["value"] for x in reading(c)["entries"]}
        for rid, name in (("digestion", "determination"), ("environment", "environment")):
            color, tone = entries[f"{rid}.color"]["number"], entries[f"{rid}.tone"]["number"]
            pair = VF.VARIABLE_COLOR_SIDES[name][color]
            assert entries[f"{rid}.subcategory"]["name"] == {"fr": pair[0 if tone <= 3 else 1][0], "en": pair[0 if tone <= 3 else 1][1]}
            sides.add(tone <= 3)
    assert sides == {True, False}  # les deux côtés ont été rencontrés


def test_every_channel_has_a_name_and_a_circuit():
    assert set(R.CHANNEL_NAMES_FR) == set(D.CHANNELS) == set(R.CHANNEL_CIRCUITS)
    assert all(R.CHANNEL_NAMES_FR[c] for c in D.CHANNELS)
    groups = {}
    for group, circuit in R.CHANNEL_CIRCUITS.values():
        assert group in R.CIRCUIT_GROUPS_FR and circuit in R.CIRCUITS_FR
        groups[group] = groups.get(group, 0) + 1
    assert groups == {"individual": 15, "tribal": 7, "collective": 14}  # 36 canaux


def test_two_rubrics_have_no_computed_content(natal):
    e = {x["id"]: x for x in reading(natal)["entries"]}
    me, sleep = e["relations.me_vs_others"], e["sleep.rhythm"]
    assert me["status"] == "pending_statistics" and sleep["status"] == "pending_rules"
    assert set(sleep["value"]) == {"type", "aura", "defined_centers", "open_centers"}  # données brutes seulement
    assert sleep["value"]["aura"]["name"] == R.AURA_FR["Generator"]


def test_reading_holds_no_interpretation_text(natal):
    """Seulement des numéros, des clés et des noms courts : aucune phrase d'interprétation."""
    def strings(x):
        if isinstance(x, str):
            yield x
        elif isinstance(x, dict):
            for k, v in x.items():
                yield from strings(v)
        elif isinstance(x, list):
            for v in x:
                yield from strings(v)
    long = [s for s in strings(reading(natal)) if len(s) > 60]
    assert not long, long
    assert all("description" not in str(e).lower() for e in reading(natal)["entries"])


def test_reading_names_live_in_the_text_files():
    folder = Path(I.__file__).parent
    for f in ("reading_fr.py", "variables_fr.py"):
        assert "À VALIDER PAR ADRIEN" in (folder / f).read_text(encoding="utf-8"), f
    assert reading(build_chart(local_to_utc(datetime(1999, 9, 20, 8, 26), "Europe/Paris").utc))["to_validate"]
