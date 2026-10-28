# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Typographie de l'habillage « atlas » : polices du site, embarquées, sans débordement."""
import dataclasses
import itertools
import re
from pathlib import Path

import pytest

from hd import data as D
from hd.bodygraph import (EMBEDDED_FONTS, SUMMARY_MAX_WIDTH, SUMMARY_SIZE, render_bodygraph,
                          summary_font_size, summary_sentence)
from hd.chart import build_chart
from hd.timeutil import local_to_utc

from .test_reference import FICTIF_1

FONTS = Path(__file__).parents[1] / "hd" / "fonts"
PROFILES = ["1/3", "1/4", "2/4", "2/5", "3/5", "3/6", "4/6", "4/1", "5/1", "5/2", "6/2", "6/3"]


@pytest.fixture(scope="module")
def chart():
    return build_chart(local_to_utc(FICTIF_1["local"], FICTIF_1["tz"]).utc)


def all_summaries(chart):
    for t, a, p in itertools.product(D.TYPES_FR, D.AUTHORITY_FR, PROFILES):
        yield summary_sentence(dataclasses.replace(chart, type=t, authority=a, profile=p))


def test_fonts_are_embedded_as_woff2(chart):
    svg = render_bodygraph(chart, skin="atlas", name="Zoé")
    for family, style, weight, file in EMBEDDED_FONTS:
        assert (FONTS / file).stat().st_size > 1000
        assert f"font-family:'{family}';font-style:{style};font-weight:{weight};" in svg
    assert svg.count("data:font/woff2;base64,") == len(EMBEDDED_FONTS)
    assert "HA Serif" not in svg and not list(FONTS.glob("ha-serif*"))


def test_each_text_uses_its_font(chart):
    svg = render_bodygraph(chart, skin="atlas", name="Zoé", uid="t")
    name = re.search(r'<text[^>]*>Zoé</text>', svg).group(0)
    assert "Instrument Serif" in name and 'font-style="italic"' in name and 'fill="url(#t-prenom)"' in name
    assert re.search(r'<text[^>]*Instrument Serif[^>]*>Design</text>', svg)
    assert re.search(r'<text[^>]*Instrument Serif[^>]*>Personnalité</text>', svg)
    assert re.search(r'font-family="Jost[^"]*" font-size="16"[^>]*>Générateur', svg)
    assert re.search(r'font-family="Jost[^"]*" font-style="italic" font-weight="300"[^>]*>', svg)
    assert re.search(r'font-family="\'Space Grotesk\'[^"]*" font-size="15" font-weight="500">\d+\.\d<', svg)
    assert re.search(r'font-family="\'Space Grotesk\'[^"]*" font-size="8.4" font-weight="600"', svg)
    assert re.search(r'font-family="\'Space Grotesk\'[^"]*" font-size="8" font-weight="500"', svg)
    assert "'DejaVu Sans'" in svg  # glyphes des planètes : police de symboles inchangée


def test_classique_is_untouched(chart):
    svg = render_bodygraph(chart, skin="classique", name="Zoé")
    assert "@font-face" not in svg and "geometricPrecision" not in svg
    assert "Jost" not in svg and "Space Grotesk" not in svg and "Instrument Serif" not in svg


def test_summary_size_shrinks_only_when_needed(chart):
    assert summary_font_size(summary_sentence(chart)) == SUMMARY_SIZE
    longest = max(all_summaries(chart), key=len)
    assert 12 <= summary_font_size(longest) < SUMMARY_SIZE


def test_no_summary_overflows_with_real_metrics(chart):
    """Mesure exacte avec la police embarquée (fontTools, outil de développement seulement)."""
    ttLib = pytest.importorskip("fontTools.ttLib")
    pytest.importorskip("brotli")
    f = ttLib.TTFont(FONTS / "jost-400.woff2")
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    for s in all_summaries(chart):
        width = sum(hmtx[cmap[ord(ch)]][0] for ch in s) / upm * summary_font_size(s)
        assert width <= SUMMARY_MAX_WIDTH, s


def test_long_name_fits(chart):
    """Prénom de 20 caractères : il tient dans la page (Instrument Serif italique, 30 px)."""
    ttLib = pytest.importorskip("fontTools.ttLib")
    pytest.importorskip("brotli")
    f = ttLib.TTFont(FONTS / "instrument-serif-italic.woff2")
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    for name in ("Marie-Gwendolyne Ölü", "Maximilien-Édouard B", "Wolfgang-Wilhelmine"):
        assert len(name) <= 20
        assert sum(hmtx[cmap[ord(ch)]][0] for ch in name) / upm * 30 <= SUMMARY_MAX_WIDTH
