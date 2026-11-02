# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Les quatre variables (flèches) : champ « variables » de l'API et dessin au-dessus de la Tête.

Ce qui est vérifié : l'orientation suit le ton (1 à 3 gauche, 4 à 6 droite), les quatre
flèches sont dans le JSON, le dessin respecte le thème, et surtout RIEN ne change quand
show_variables est faux (SVG identiques à l'octet aux golden, atlas et gdh).

Les valeurs couleur / ton / base des naissances FICTIVES sont celles que le moteur calcule
aujourd'hui : valeurs de non-régression, à vérifier dans une appli de référence.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

from hd import data as D
from hd import precision as P
from hd import variables_fr as VF
from hd.bodygraph import PAGE_H, PAGE_W, render_bodygraph, variables_band
from hd.chart import Activation, build_chart
from hd.themes import PUBLIC_THEMES, THEMES
from hd.timeutil import local_to_utc

from .test_api import FICTIF_1 as API_FICTIF_1, KEY, call
from .test_reference import FICTIFS

GOLDEN = Path(__file__).with_name("golden")
PRIVATE = Path(__file__).with_name("references_privees.json")
SVG_NS = "{http://www.w3.org/2000/svg}"
NAMES = ("determination", "environment", "motivation", "perspective")

# Mêmes naissances fictives que tests/golden/theme-*-N.svg.
DATES = [(datetime(2000, 1, 1, 12, 0), "Europe/Paris"), (datetime(1975, 11, 3, 22, 45), "America/New_York"),
         (datetime(2012, 6, 21, 4, 10), "Asia/Tokyo")]


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", KEY)


def _chart(i):
    local, tz = DATES[i - 1]
    return build_chart(local_to_utc(local, tz).utc)


def _fictif(i):
    ref = FICTIFS[i - 1]
    return build_chart(local_to_utc(ref["local"], ref["tz"]).utc)


def _fake_chart(tones):
    """Thème minimal dont les quatre flèches ont les tons donnés (ordre : Digestion, Environnement,
    Motivation, Perspective)."""
    act = lambda planet, tone: Activation(planet, 0.0, 1, 1, 3, tone, 1)
    t1, t2, t3, t4 = tones
    side = lambda a, b: {"sun": act("sun", a), "north_node": act("north_node", b)}
    return SimpleNamespace(
        design=side(t1, t2), personality=side(t3, t4),
        variables={"design_sun": "gauche" if t1 <= 3 else "droite", "design_node": "gauche" if t2 <= 3 else "droite",
                   "personality_sun": "gauche" if t3 <= 3 else "droite",
                   "personality_node": "gauche" if t4 <= 3 else "droite"})


def _groups(svg):
    root = ElementTree.fromstring(svg)
    return root, {g.get("class").split("-", 1)[1]: g for g in root.iter(f"{SVG_NS}g")
                  if (g.get("class") or "").startswith("variable ")}


def _points(group):
    d = group.find(f"{SVG_NS}path").get("d")
    return [tuple(float(v) for v in pt.split(",")) for pt in re.findall(r"-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?", d)]


# ---------------------------------------------------------------- orientation selon le ton

@pytest.mark.parametrize("tone,expected", [(1, "left"), (2, "left"), (3, "left"),
                                           (4, "right"), (5, "right"), (6, "right")])
def test_orientation_follows_the_tone(tone, expected):
    assert P.orientation(tone) == expected
    v = P.variables(_fake_chart((tone,) * 4))
    assert [v[n]["orientation"] for n in NAMES] == [expected] * 4
    assert all(v[n]["tone"] == tone for n in NAMES)


def test_orientation_agrees_with_the_existing_direction():
    for i in range(1, 6):
        for name, x in P.variables(_fictif(i)).items():
            assert x["orientation"] == {"gauche": "left", "droite": "right"}[x["direction"]], (i, name)


def test_each_arrow_comes_from_the_requested_body():
    v = P.variables(_fictif(1))
    assert [(v[n]["side"], v[n]["planet"]) for n in NAMES] == [
        ("design", "sun"), ("design", "north_node"), ("personality", "sun"), ("personality", "north_node")]


# ---------------------------------------------------------------- JSON de /v1/chart

def test_api_returns_the_four_variables_by_default():
    code, r = call({**API_FICTIF_1, "include_svg": False})
    assert code == 200
    assert list(r["variables"]) == list(NAMES)
    for x in r["variables"].values():
        assert x["orientation"] in ("left", "right")
        assert 1 <= x["color"] <= 6 and 1 <= x["tone"] <= 6 and 1 <= x["base"] <= 5
        assert x["title"] and x["label"].startswith(x["title"])


def test_api_variables_of_fictif_1():
    """Non-régression (naissance fictive) : à vérifier dans une appli de référence."""
    code, r = call({**API_FICTIF_1, "include_svg": False})
    got = {n: (x["orientation"], x["color"], x["tone"], x["base"]) for n, x in r["variables"].items()}
    assert got == {"determination": ("left", 5, 2, 4), "environment": ("right", 4, 6, 1),
                   "motivation": ("left", 4, 3, 5), "perspective": ("right", 6, 6, 2)}
    assert [x["label"] for x in r["variables"].values()] == [
        "Digestion : Son Aigu", "Environnement : Montagnes Passif", "Motivation : Besoin",
        "Perspective : Personnel / Pouvoir"]


@pytest.mark.parametrize("i,expected", [
    (2, {"determination": ("right", 6, 5, 5), "environment": ("right", 3, 4, 1),
         "motivation": ("left", 6, 1, 1), "perspective": ("left", 3, 2, 1)}),
    (3, {"determination": ("right", 4, 5, 2), "environment": ("left", 2, 1, 4),
         "motivation": ("right", 3, 6, 3), "perspective": ("right", 3, 6, 5)}),
    (4, {"determination": ("left", 6, 1, 1), "environment": ("right", 2, 6, 2),
         "motivation": ("left", 5, 2, 2), "perspective": ("right", 2, 4, 1)}),
    (5, {"determination": ("left", 3, 2, 4), "environment": ("right", 3, 4, 5),
         "motivation": ("left", 2, 3, 5), "perspective": ("right", 4, 6, 3)}),
])
def test_variables_of_the_other_fictional_births(i, expected):
    """Non-régression (naissances fictives) : à vérifier dans une appli de référence."""
    got = {n: (x["orientation"], x["color"], x["tone"], x["base"]) for n, x in P.variables(_fictif(i)).items()}
    assert got == expected


@pytest.mark.skip(reason="en attente de référence : couleur, ton et base des 4 variables de naissances réelles "
                         "(à vérifier dans une appli de référence, comme test_variables_match_reference_app)")
def test_variables_match_reference_app_colors():
    raise AssertionError


@pytest.mark.skipif(not PRIVATE.exists(), reason="tests/references_privees.json absent (fichier local, ignoré par git)")
def test_private_references_orientation():
    """Naissances de personnes réelles, hors dépôt : l'orientation redit les flèches de l'appli de référence."""
    for ref in json.loads(PRIVATE.read_text(encoding="utf-8"))["references"]:
        c = build_chart(local_to_utc(datetime.fromisoformat(ref["local"]), ref["tz"]).utc)
        got = [P.variables(c)[n]["orientation"] for n in NAMES]
        assert got == [{"gauche": "left", "droite": "right"}[d] for d in ref["variables"]], ref["nom"]


def test_existing_json_fields_are_untouched():
    """details.variables garde ses valeurs « gauche » / « droite » ; seuls des champs s'ajoutent."""
    code, r = call({**API_FICTIF_1})
    assert r["details"]["variables"] == {"design_sun": "gauche", "design_node": "droite",
                                         "personality_sun": "gauche", "personality_node": "droite"}
    assert set(r) == {"type", "type_fr", "authority", "authority_fr", "profile", "profile_label", "cross",
                      "channels", "defined_centers", "definition", "active_gates", "summary", "place_resolved",
                      "time_warning", "details", "svg", "variables"}


def test_variables_are_the_same_with_and_without_details():
    _, plain = call({**API_FICTIF_1, "include_svg": False})
    _, full = call({**API_FICTIF_1, "include_svg": False, "details": True})
    assert plain["variables"] == full["variables"]


def test_show_variables_does_not_change_the_json():
    _, a = call({**API_FICTIF_1})
    _, b = call({**API_FICTIF_1, "show_variables": True, "variable_labels": True})
    a.pop("svg"), b.pop("svg")
    assert a == b


# ---------------------------------------------------------------- options de l'API

@pytest.mark.parametrize("field", ["show_variables", "variable_labels"])
@pytest.mark.parametrize("value", ["oui", "true", 1, 0])
def test_options_must_be_booleans(field, value):
    code, r = call({**API_FICTIF_1, field: value})
    assert code == 400 and r["error"]["code"] == "invalid_field"


@pytest.mark.parametrize("path,body", [
    ("/v1/composite", lambda p: {"people": [p, p]}),
    ("/v1/group", lambda p: {"people": [p, p, p]}),
    ("/v1/return", lambda p: {"chart": p, "kind": "solar", "year": 2020}),
    ("/v1/transit", lambda p: {"chart": p}),
])
def test_chart_only_options_are_refused_elsewhere(path, body):
    for field in ("show_variables", "variable_labels"):
        code, r = call(body({**API_FICTIF_1, field: True}), path=path)
        assert code == 400 and r["error"]["code"] == "unknown_field", (path, field)


def test_api_svg_with_and_without_the_option():
    _, plain = call({**API_FICTIF_1})
    _, off = call({**API_FICTIF_1, "show_variables": False})
    _, on = call({**API_FICTIF_1, "show_variables": True})
    assert 'viewBox="0 0 616 840"' in plain["svg"] and 'viewBox="0 0 616 840"' in off["svg"]
    assert "variable-determination" not in plain["svg"] and "variable-determination" not in off["svg"]
    assert "variable-determination" in on["svg"]
    for theme in PUBLIC_THEMES:
        _, r = call({**API_FICTIF_1, "theme": theme, "show_variables": True})
        ElementTree.fromstring(r["svg"])


def test_variable_labels_need_show_variables():
    _, labels_only = call({**API_FICTIF_1, "variable_labels": True})
    _, plain = call({**API_FICTIF_1})
    assert 'viewBox="0 0 616 840"' in labels_only["svg"] and "variable-" not in labels_only["svg"]
    assert labels_only["svg"].count("<text") == plain["svg"].count("<text")


# ---------------------------------------------------------------- non-régression : rien ne change par défaut

@pytest.mark.parametrize("theme", PUBLIC_THEMES)
@pytest.mark.parametrize("i", range(1, 4))
def test_svg_is_byte_identical_to_the_golden_without_the_option(theme, i):
    """tests/golden/theme-{atlas,gdh}-N.svg : produits avant cette option."""
    golden = (GOLDEN / f"theme-{theme}-{i}.svg").read_text(encoding="utf-8")
    c = _chart(i)
    assert render_bodygraph(c, theme=theme, name="Exemple", uid="hdtest0001") == golden
    assert render_bodygraph(c, theme=theme, name="Exemple", uid="hdtest0001",
                            show_variables=False, variable_labels=False) == golden
    # variable_labels seul ne dessine rien non plus
    assert render_bodygraph(c, theme=theme, name="Exemple", uid="hdtest0001", variable_labels=True) == golden


@pytest.mark.parametrize("skin", ["classique", "atlas"])
@pytest.mark.parametrize("i", range(1, 6))
def test_fictif_goldens_are_unchanged(skin, i):
    """Mêmes cartes que tests/test_svg_ids.py (golden sans préfixe d'identifiant), option explicitement fausse."""
    golden = (GOLDEN / f"fictif-{i}-{skin}.svg").read_text(encoding="utf-8")
    svg = render_bodygraph(_fictif(i), skin=skin, name=f"Fictif {i} & <test>", uid="hdtest0001", show_variables=False)
    assert svg.replace('id="hdtest0001-', 'id="').replace("url(#hdtest0001-", "url(#") == golden


def test_the_card_is_the_same_apart_from_the_frame_the_background_and_the_arrows():
    """Avec l'option, le dessin d'origine ne bouge pas : seuls le cadre, le fond et les flèches changent."""
    for theme in ("atlas", "gdh"):
        c = _chart(1)
        off = render_bodygraph(c, theme=theme, name="Exemple", uid="u")
        on = render_bodygraph(c, theme=theme, name="Exemple", uid="u", show_variables=True)
        band = variables_band(False)
        no_arrows = re.sub(r'<g class="variable .*?</g>\n  ', "", on, flags=re.S)
        assert no_arrows.count("variable") == 0
        no_arrows = no_arrows.replace(f'viewBox="0 {-band} {PAGE_W} {PAGE_H + band}"', 'viewBox="0 0 616 840"')
        no_arrows = no_arrows.replace(f'height="{PAGE_H + band}"', 'height="840"', 1)
        # fond : le rectangle prolongé vers le haut redevient celui de la page
        no_arrows = no_arrows.replace(f'y="{-band}" width="{PAGE_W}" height="{PAGE_H + band}"', f'width="{PAGE_W}" height="{PAGE_H}"')
        assert no_arrows == off, theme


# ---------------------------------------------------------------- le dessin

def test_frame_grows_upward_only_with_the_option():
    c = _chart(1)
    off = ElementTree.fromstring(render_bodygraph(c, theme="atlas", name="E", uid="u"))
    assert (off.get("viewBox"), off.get("width"), off.get("height")) == ("0 0 616 840", "616", "840")
    for labels in (False, True):
        band = variables_band(labels)
        on = ElementTree.fromstring(render_bodygraph(c, theme="atlas", name="E", uid="u",
                                                     show_variables=True, variable_labels=labels))
        assert on.get("viewBox") == f"0 {-band} 616 {840 + band}"
        assert (on.get("width"), on.get("height")) == ("616", str(840 + band))
    assert variables_band(True) > variables_band(False) > 0


@pytest.mark.parametrize("theme", ["atlas", "gdh", "classique"])
def test_four_arrows_follow_the_tones_and_the_layout(theme):
    c = _chart(1)
    svg = render_bodygraph(c, theme=theme, name="E", uid="u", show_variables=True)
    root, groups = _groups(svg)
    assert list(groups) == list(NAMES)
    axis = 108 + 200
    v = P.variables(c)
    pts = {n: _points(g) for n, g in groups.items()}
    for n in NAMES:
        g = groups[n]
        assert g.get("data-orientation") == v[n]["orientation"]
        xs = [x for x, _ in pts[n]]
        tip = pts[n][3]  # sommets : queue, cou, aile, POINTE, aile, cou, queue
        assert tip[0] == (min(xs) if v[n]["orientation"] == "left" else max(xs))
        assert tip[1] == (pts[n][0][1] + pts[n][-1][1]) / 2  # la pointe est dans l'axe de la tige
    # Design à gauche de l'axe de la Tête, Personnalité à droite ; Digestion au-dessus d'Environnement.
    assert all(max(x for x, _ in pts[n]) < axis for n in ("determination", "environment"))
    assert all(min(x for x, _ in pts[n]) > axis for n in ("motivation", "perspective"))
    cy = lambda n: pts[n][3][1]
    assert cy("determination") < cy("environment") and cy("motivation") < cy("perspective")
    assert cy("determination") == cy("motivation") and cy("environment") == cy("perspective")
    assert all(cy(n) < 0 for n in NAMES)  # dans la bande ajoutée, au-dessus de la page


def test_arrow_colors_come_from_the_theme():
    c = _chart(1)
    for theme in ("atlas", "gdh", "classique"):
        t = THEMES[theme]
        _, groups = _groups(render_bodygraph(c, theme=theme, name="E", uid="u", show_variables=True))
        for n, side in (("determination", "variable_design"), ("environment", "variable_design"),
                        ("motivation", "variable_personality"), ("perspective", "variable_personality")):
            assert groups[n].find(f"{SVG_NS}path").get("fill") == t[side], (theme, n)
    # atlas et gdh n'ont pas les mêmes couleurs de flèches
    assert THEMES["atlas"]["variable_design"] != THEMES["gdh"]["variable_design"]
    assert THEMES["atlas"]["variable_personality"] != THEMES["gdh"]["variable_personality"]


@pytest.mark.parametrize("theme", sorted(THEMES))
def test_every_theme_declares_the_arrow_colors(theme):
    for key in ("variable_design", "variable_personality", "variable_label"):
        assert re.fullmatch(r"#[0-9a-fA-F]{6}", THEMES[theme][key]), (theme, key)


def test_labels_are_optional_and_come_from_the_text_file():
    c = _chart(1)
    plain = render_bodygraph(c, theme="atlas", name="E", uid="u", show_variables=True)
    labeled = render_bodygraph(c, theme="atlas", name="E", uid="u", show_variables=True, variable_labels=True)
    _, g_plain = _groups(plain)
    _, g_lab = _groups(labeled)
    for n in NAMES:
        assert g_plain[n].find(f"{SVG_NS}text") is None
        assert g_lab[n].find(f"{SVG_NS}text").text == VF.ARROW_TITLES[n]
    assert [VF.ARROW_TITLES[n] for n in NAMES] == ["Digestion", "Environnement", "Motivation", "Perspective"]


def test_arrows_are_described_for_screen_readers():
    _, groups = _groups(render_bodygraph(_chart(1), theme="gdh", name="E", uid="u", show_variables=True))
    for n, g in groups.items():
        assert g.get("role") == "img" and g.get("aria-label") == g.find(f"{SVG_NS}title").text
        assert g.get("aria-label").endswith(f"flèche vers la {VF.ARROW_SENS[g.get('data-orientation')]}")


def test_show_variables_needs_a_chart():
    with pytest.raises(ValueError):
        render_bodygraph(active_gates={1: ["design"]}, show_variables=True)


def test_arrows_add_no_xml_id():
    ids = lambda s: re.findall(r'\bid="([^"]+)"', s)
    c = _chart(1)
    assert ids(render_bodygraph(c, theme="gdh", uid="u", show_variables=True, variable_labels=True)) == \
        ids(render_bodygraph(c, theme="gdh", uid="u"))


# ---------------------------------------------------------------- textes (hd/variables_fr.py)

def test_text_file_is_complete_and_flagged_for_review():
    for name in NAMES:
        assert set(D.VARIABLE_COLOR_NAMES[name]) == set(range(1, 7))
        assert all(fr and en for fr, en in D.VARIABLE_COLOR_NAMES[name].values())
        assert VF.ARROW_TITLES[name] and VF.LABEL_FORMATS[name]
    assert D.VARIABLE_COLOR_NAMES is VF.VARIABLE_COLOR_NAMES and D.TONE_SENSES is VF.TONE_SENSES
    assert "À VALIDER PAR ADRIEN" in Path(VF.__file__).read_text(encoding="utf-8")


def test_french_color_names_of_the_digestion_arrow():
    assert [fr for fr, _ in D.VARIABLE_COLOR_NAMES["determination"].values()] == \
        ["Appétit", "Goût", "Soif", "Toucher", "Son", "Lumière"]
