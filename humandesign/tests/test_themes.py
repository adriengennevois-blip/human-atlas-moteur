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
from hd.data import GATE_CENTER
from hd.themes import ATLAS, CLASSIQUE, GDH, THEMES, contrast
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


ATLAS_BRAND = {"#e07a1f", "#6b2fa3", "#d6cee2", "#efebf3", "#dcd6e2", "#7b22aa", "#cd7a18"}  # orange, violet, lavande
GDH_COLOR_KEYS = {"design", "personality", "design_text", "personality_text", "name_from", "name_to",
                  "channel_inactive", "variable_design", "variable_personality", "legend_design",
                  "legend_personality", "background", "id_prefix"}
GDH_BG_COLOR_KEYS = {"top", "bottom", "halo", "veil", "orbit", "dot_violet", "dot_orange"}


def test_gdh_inherits_atlas_and_overrides_only_colors():
    changed = {k for k in GDH if k not in ATLAS or GDH[k] != ATLAS[k]}
    assert changed <= GDH_COLOR_KEYS, changed - GDH_COLOR_KEYS
    assert set(GDH) - {"id_prefix"} == set(ATLAS)  # aucune option ajoutée ni retirée (id_prefix : identifiants, pas une couleur)
    bg_changed = {k for k in GDH["background"] if GDH["background"][k] != ATLAS["background"][k]}
    assert bg_changed <= GDH_BG_COLOR_KEYS and GDH["background"]["kind"] == "atmosphere"
    # tout ce qui change est une couleur « #rrggbb » (ou le nom de la couleur dans la légende)
    for k in changed - {"background", "id_prefix", "legend_design", "legend_personality"}:
        assert re.fullmatch(r"#[0-9a-fA-F]{6}", GDH[k]), k
    # centres, contours, polices, tailles : repris d'atlas tels quels
    for k in ("center_defined", "center_open", "center_open_stroke", "center_stroke", "center_glow", "text",
              "muted", "gate_text", "gate_text_on", "font_num", "font_title", "font_text", "num_weights",
              "variable_label"):
        assert GDH[k] == ATLAS[k], k


def test_gdh_colors(gdh):
    for color in ("#B8893B", "#8C6A2E", "#2B3550", "#E6DED0", "#FFFDF8", "#EFE6D3", "#F6F1E7"):
        assert color in gdh, color
    found = {c.lower() for c in HEX.findall(gdh)}
    assert not found & ATLAS_BRAND, found & ATLAS_BRAND  # ni orange, ni violet, ni lavande d'atlas
    assert "<feTurbulence" not in gdh and "marbre" not in gdh  # plus de fond marbré


def test_gdh_defined_centers_use_the_atlas_colors(gdh):
    for center in _chart(1).defined_centers:
        color = ATLAS["center_defined"][center]
        assert re.search(rf'id="gdh-hdtest0001-center-{center}" d="[^"]+" fill="{color}" stroke="#ffffff"', gdh), center
    assert 'filter="url(#gdh-hdtest0001-glow)"' in gdh  # même lueur autour des centres définis


def test_gdh_ids_are_prefixed(gdh):
    ids = IDS.findall(gdh)
    assert ids and all(i.startswith("gdh-hdtest0001-") for i in ids)
    assert {"gdh-hdtest0001-bg", "gdh-hdtest0001-halo", "gdh-hdtest0001-glow"} <= set(ids)
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
        assert strokes[:2] == [("#B8893B", ""), ("#2B3550", f'stroke-dasharray="{GDH["both_dash"]}"')]


# ---------------------------------------------------------------- gdh = atlas, aux couleurs près

COLOR = re.compile(r"#[0-9a-fA-F]{6}\b")
BRAND_WORDS = re.compile(r">(orange|violet|or|bleu nuit)</tspan>")  # légende : nom de la couleur du thème


def _colorless(svg):
    """Le SVG sans aucune valeur de couleur : ne reste que la structure (formes, positions, tailles, textes)."""
    svg = COLOR.sub("#", svg)
    svg = re.sub(r'(?<=id=")gdh-|(?<=url\(#)gdh-', "", svg)  # préfixe des identifiants (pas une couleur)
    return BRAND_WORDS.sub(">couleur</tspan>", svg)


@pytest.mark.parametrize("variables", [False, True])
@pytest.mark.parametrize("i", range(1, 4))
def test_gdh_and_atlas_differ_only_by_color_values(i, variables):
    """Même structure, mêmes formes, mêmes positions : seules les valeurs de couleur diffèrent."""
    c = _chart(i)
    kw = dict(name="Exemple", uid="hdtest0001", show_variables=variables, variable_labels=variables)
    atlas, gdh = render_bodygraph(c, theme="atlas", **kw), render_bodygraph(c, theme="gdh", **kw)
    assert atlas != gdh and len(COLOR.findall(atlas)) == len(COLOR.findall(gdh))
    assert _colorless(atlas) == _colorless(gdh)


def _contrast_pairs(theme):
    """Couples (texte, fond) qui font la lisibilité d'une carte, tirés du thème."""
    t, bg = THEMES[theme], THEMES[theme]["background"]
    pairs = {
        "numéro sur pastille Design": (t["gate_text_on"], t["design"]),
        "numéro sur pastille Personnalité": (t["gate_text_on"], t["personality"]),
        "numéro de porte inactive, centre ouvert": (t["gate_text"], t["center_open"]),
    }
    for center, fill in t["center_defined"].items():
        pairs[f"numéro de porte inactive, centre {center} défini"] = (t["gate_text_defined"], fill)
        pairs[f"numéro sur pastille, centre {center} (cerclage)"] = (t["gate_text_on"], fill)
    for where in ("top", "bottom"):
        for label, key in (("Design", "design_text"), ("Personnalité", "personality_text"),
                           ("texte", "text"), ("légende", "muted")):
            pairs[f"{label} sur le fond ({where})"] = (t[key], bg[where])
    return pairs


def test_gdh_readability_is_at_least_atlas():
    """Numéros de portes, valeurs des planètes et textes : contraste WCAG au moins égal à celui d'atlas."""
    atlas, gdh = _contrast_pairs("atlas"), _contrast_pairs("gdh")
    assert atlas.keys() == gdh.keys()
    for name in atlas:
        assert contrast(*gdh[name]) >= contrast(*atlas[name]) - 1e-9, (name, contrast(*gdh[name]), contrast(*atlas[name]))
    # les numéros blancs sur pastille : or et bleu nuit au moins aussi lisibles qu'orange et violet
    assert contrast("#ffffff", GDH["design"]) >= contrast("#ffffff", ATLAS["design"])
    assert contrast("#ffffff", GDH["personality"]) >= contrast("#ffffff", ATLAS["personality"])


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
