# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Thèmes de couleurs : atlas (Human Atlas, inchangé) et gdh (GoDesignHumain)."""
import re
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

import pytest

from hd.bodygraph import render_bodygraph
from hd.chart import build_chart
from hd.themes import CLASSIQUE, GDH, THEMES
from hd.timeutil import local_to_utc

from .test_api import KEY, call

GOLDEN = Path(__file__).with_name("golden")
HD = Path(__file__).parents[1] / "hd"
IDS = re.compile(r'\bid="([^"]+)"')
REFS_TO_IDS = re.compile(r'url\(#([^)]+)\)')
HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")

# Naissances fictives (jamais une vraie personne).
DATES = [(datetime(2000, 1, 1, 12, 0), "Europe/Paris"), (datetime(1975, 11, 3, 22, 45), "America/New_York"),
         (datetime(2012, 6, 21, 4, 10), "Asia/Tokyo")]
PERSON = {"date": "2000-01-01", "time": "12:00", "time_precision": "exacte", "tz": "Europe/Paris", "name": "Exemple"}


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", KEY)


def _chart(i):
    local, tz = DATES[i - 1]
    return build_chart(local_to_utc(local, tz).utc)


# ---------------------------------------------------------------- atlas : rien ne change

@pytest.mark.parametrize("i", range(1, 4))
def test_atlas_is_identical_to_before(i):
    """tests/golden/theme-atlas-*.svg : rendus produits AVANT la création de hd/themes.py."""
    svg = render_bodygraph(_chart(i), theme="atlas", name="Exemple", uid="hdtest0001")
    assert svg == (GOLDEN / f"theme-atlas-{i}.svg").read_text(encoding="utf-8")


def test_atlas_is_the_default_theme():
    c = _chart(1)
    assert render_bodygraph(c, uid="x") == render_bodygraph(c, theme="atlas", uid="x")


def test_colors_live_only_in_the_theme_module():
    for f in ("bodygraph.py", "svg.py", "composite.py"):
        assert not HEX.findall((HD / f).read_text(encoding="utf-8")), f


# ---------------------------------------------------------------- gdh

@pytest.fixture(scope="module")
def gdh():
    return render_bodygraph(_chart(1), theme="gdh", name="Exemple", uid="hdtest0001")


def test_gdh_is_valid_svg(gdh):
    root = ElementTree.fromstring(gdh)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"


def test_gdh_colors(gdh):
    for color in ("#F6F1E7", "#E9D7A4", "#C9A45C", "#9C7A35", "#8C6A2E", "#2B3550", "#141A2B",
                  "#FBF8F1", "#E6DED0", "#3A3326"):
        assert color in gdh, color
    for color in set(HEX.findall(gdh)):  # aucune couleur d'Atlas ne déborde
        assert color.lower() not in {"#e07a1f", "#6b2fa3", "#d6cee2", "#efebf3", "#7b22aa"}, color


def test_gdh_marble_veins(gdh):
    turb = re.search(r'<feTurbulence type="fractalNoise" baseFrequency="([\d.]+)" numOctaves="(\d)"', gdh)
    assert turb and float(turb.group(1)) == pytest.approx(0.012) and turb.group(2) == "3"
    assert "<feColorMatrix" in gdh
    table = re.search(r'tableValues="([^"]+)"', gdh).group(1)
    assert max(float(v) for v in table.split()) <= 0.12  # veines à 12 % au plus
    # le même veinage sur le fond et sur chaque centre défini
    marble = "url(#gdh-hdtest0001-marbre)"
    assert gdh.count(marble) == 1 + len(_chart(1).defined_centers)


def test_gdh_ids_are_prefixed(gdh):
    ids = IDS.findall(gdh)
    assert ids and all(i.startswith("gdh-hdtest0001-") for i in ids)
    assert {"gdh-hdtest0001-or", "gdh-hdtest0001-nuit", "gdh-hdtest0001-or-centre",
            "gdh-hdtest0001-marbre"} <= set(ids)
    assert len(ids) == len(set(ids)) and set(REFS_TO_IDS.findall(gdh)) <= set(ids)


def test_two_gdh_cards_share_no_id():
    c = _chart(1)
    a, b = render_bodygraph(c, theme="gdh"), render_bodygraph(c, theme="gdh")
    assert not set(IDS.findall(a)) & set(IDS.findall(b))


def test_gdh_channel_on_both_sides_is_half_gold_half_night_blue():
    c = _chart(3)  # portes 16, 17, 55 et 58 activées des deux côtés
    gdh = render_bodygraph(c, theme="gdh", uid="hdtest0001")
    both = [g for g, s in c.active_gates.items() if s == ["design", "personality"]]
    assert both
    for g in both:
        strokes = re.findall(rf'class="gate-{g}" d="[^"]+" stroke="([^"]+)"[^>]*?(stroke-dasharray="[^"]+")?/>', gdh)
        assert strokes[:2] == [("url(#gdh-hdtest0001-or)", ""),
                               ("url(#gdh-hdtest0001-nuit)", f'stroke-dasharray="{GDH["both_dash"]}"')]


def test_gdh_gate_numbers(gdh):
    c = _chart(1)
    # porte inactive d'un centre ouvert : brun ; d'un centre défini : ivoire
    assert re.search(r'fill="#3A3326">64</text>', gdh) and "head" not in c.defined_centers
    assert re.search(r'fill="#FBF8F1">62</text>', gdh) and "throat" in c.defined_centers


def test_themes_change_nothing_but_colors():
    c = _chart(2)
    strip = lambda s: re.sub(r'(fill|stroke|stop-color|filter|id)="[^"]*"', "", s)
    a, g = render_bodygraph(c, theme="atlas", uid="u"), render_bodygraph(c, theme="gdh", uid="u")
    gate_paths = lambda s: re.findall(r'class="gate-\d+" d="[^"]+"', s)
    assert gate_paths(a) == gate_paths(g)  # mêmes canaux activés, aux mêmes endroits
    numbers = lambda s: re.findall(r'text-anchor="middle"[^>]*>(\d+)</text>', strip(s))
    assert numbers(a) == numbers(g)


def test_every_theme_has_every_required_key():
    keys = set(CLASSIQUE)  # le thème minimal : les autres ajoutent des options (légende, prénom en dégradé)
    for name, t in THEMES.items():
        assert keys <= set(t), (name, keys - set(t))


# ---------------------------------------------------------------- API

def test_api_theme_gdh():
    code, r = call({**PERSON, "theme": "gdh"})
    assert code == 200
    ElementTree.fromstring(r["svg"])
    assert "#F6F1E7" in r["svg"] and 'id="gdh-hd' in r["svg"]


def test_api_theme_atlas_is_the_default():
    code, a = call({**PERSON, "theme": "atlas"})
    code_b, b = call(PERSON)
    strip = lambda s: re.sub(r"hd[0-9a-f]{8}", "UID", s)
    assert code == code_b == 200 and strip(a["svg"]) == strip(b["svg"])


@pytest.mark.parametrize("body", [
    {**PERSON, "theme": "rose"}, {**PERSON, "theme": "classique"}, {**PERSON, "theme": "composite"},
    {**PERSON, "theme": 1}, {**PERSON, "theme": None}, {**PERSON, "theme": "gdh", "skin": "atlas"},
])
def test_api_unknown_theme_is_422(body):
    code, r = call(body)
    assert code == 422 and r["error"]["code"] == "invalid_theme"


def test_theme_is_not_accepted_per_person():
    code, _ = call({"people": [PERSON, {**PERSON, "theme": "gdh"}]}, path="/v1/composite")
    assert code == 400
