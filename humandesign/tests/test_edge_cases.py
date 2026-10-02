# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Cas limites trouvés à la relecture (étape 3). Aucun test n'utilise le réseau."""
import time
from datetime import datetime
from xml.etree import ElementTree

import pytest

from hd import data as D
from hd import timeutil
from hd.bodygraph import render_bodygraph, validate_template
from hd.chart import activation, build_chart
from hd.timeutil import GeocodingUnavailable, geocode, local_to_utc


@pytest.fixture(scope="module")
def chart():
    return build_chart(local_to_utc(datetime(1999, 9, 20, 8, 26), "Europe/Paris").utc)


# ---------------------------------------------------------------- frontières

def test_planet_exactly_on_gate_and_line_boundaries():
    """Une planète pile sur une frontière appartient à la porte / ligne qui commence là.
    Juste avant (1e-9°, bien en dessous de la précision des éphémérides), elle est
    dans la ligne précédente, y compris au passage 360° → 0°."""
    eps = 1e-9
    for k in range(64 * 6):
        b = (D.WHEEL_START + k * D.LINE_ARC) % 360
        a = activation("sun", b)
        assert (a.gate, a.line) == (D.GATE_ORDER[k // 6], k % 6 + 1)
        before = activation("sun", (b - eps) % 360)
        prev = (k - 1) % (64 * 6)
        assert (before.gate, before.line) == (D.GATE_ORDER[prev // 6], prev % 6 + 1)
        for x in (a, before):
            assert 1 <= x.color <= 6 and 1 <= x.tone <= 6 and 1 <= x.base <= 5


def test_longitude_360_is_the_same_as_0():
    assert activation("sun", 360.0).label == activation("sun", 0.0).label


# ---------------------------------------------------------------- changement d'heure

def test_dst_gap_message_says_which_offset_was_used():
    """Bug : avec fold=1, le message disait « notée à l'ancienne heure » alors que
    le calcul utilisait la nouvelle heure."""
    old = local_to_utc(datetime(2021, 3, 28, 2, 30), "Europe/Paris", fold=0)
    new = local_to_utc(datetime(2021, 3, 28, 2, 30), "Europe/Paris", fold=1)
    assert "inexistante" in old.warning and "UTC+1" in old.warning
    assert "inexistante" in new.warning and "UTC+2" in new.warning


def test_dst_ambiguous_message_is_readable():
    amb = local_to_utc(datetime(2021, 10, 31, 2, 30), "Europe/Paris")
    assert "ambiguë" in amb.warning and "UTC+2" in amb.warning
    assert "fold" not in amb.warning  # pas de jargon technique dans le message montré à l'app


# ---------------------------------------------------------------- lieu

def _fake_search(results):
    return lambda query: results


def test_place_not_found(monkeypatch):
    monkeypatch.setattr(timeutil, "_search", _fake_search([]))
    with pytest.raises(ValueError, match="introuvable"):
        geocode("zzqxqzzq")


def test_geocoding_service_down(monkeypatch):
    from geopy.exc import GeocoderTimedOut

    def boom(query):
        raise GeocoderTimedOut("lent")
    monkeypatch.setattr(timeutil, "_search", boom)
    with pytest.raises(GeocodingUnavailable):
        geocode("Lyon")


def test_ambiguous_place_in_another_timezone_is_flagged(monkeypatch):
    """Bug : « Saint-Denis » renvoyait Saint-Denis (93) sans prévenir, alors que
    Saint-Denis de La Réunion est à UTC+4 : le thème aurait été faux de 2-3 heures."""
    monkeypatch.setattr(timeutil, "_search", _fake_search([
        ("Saint-Denis, Seine-Saint-Denis, France", 48.94, 2.36),
        ("Saint-Denis, Seine-Saint-Denis, France", 48.94, 2.36),
        ("Saint-Denis, La Réunion, France", -20.88, 55.45),
        ("Saint-Denis, Carcassonne, Aude, France", 43.36, 2.22),
    ]))
    p = geocode("Saint-Denis")
    assert p.tz == "Europe/Paris"
    assert p.alternatives == ["Saint-Denis, La Réunion, France (Indian/Reunion)"]


def test_homonyms_in_the_same_timezone_are_not_a_problem(monkeypatch):
    """Le lieu ne sert qu'à trouver le fuseau : deux villes du même fuseau donnent le même thème."""
    monkeypatch.setattr(timeutil, "_search", _fake_search([
        ("Saint-Denis, Seine-Saint-Denis, France", 48.94, 2.36),
        ("Saint-Denis, Carcassonne, Aude, France", 43.36, 2.22),
    ]))
    assert geocode("Saint-Denis").alternatives == []


# ---------------------------------------------------------------- prénom dans le SVG

@pytest.mark.parametrize("name", ['<script>"A & B"</script>', "O'Neil & <Zoé>", 'Guillemets "doubles"'])
def test_name_is_escaped(chart, name):
    svg = render_bodygraph(chart, skin="atlas", name=name)
    ElementTree.fromstring(svg)
    assert "<script>" not in svg


@pytest.mark.parametrize("name", ["Zoé\x01\x0b", "a\ud800b", "tab\tet\nligne"])
def test_name_with_invalid_xml_characters_does_not_break_the_svg(chart, name):
    """Bug : un caractère de contrôle (ou un demi-caractère Unicode, possible via
    JSON « \\ud800 ») rendait le SVG illisible, voire faisait planter le rendu."""
    for skin in ("atlas", "classique"):
        svg = render_bodygraph(chart, skin=skin, name=name)
        ElementTree.fromstring(svg.encode("utf-8"))


# ---------------------------------------------------------------- vitesse

def test_template_is_checked_once_not_on_every_render(chart):
    """Bug de performance : le gabarit (fixe) était revérifié à chaque carte,
    soit ~1,5 s de calcul inutile par appel de l'API."""
    validate_template()
    t = time.perf_counter()
    for _ in range(3):
        render_bodygraph(chart, skin="atlas")
    assert time.perf_counter() - t < 1.0
