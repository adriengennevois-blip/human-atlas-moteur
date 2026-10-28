# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Identifiants internes du SVG : uniques à chaque carte, sans changer le rendu."""
import re
from pathlib import Path

import pytest

from hd.bodygraph import SKINS, render_bodygraph
from hd.chart import build_chart
from hd.timeutil import local_to_utc

from .test_reference import FICTIF_1, FICTIF_3, FICTIF_4, FICTIF_5, FICTIF_2

GOLDEN = Path(__file__).with_name("golden")
REFS = [FICTIF_1, FICTIF_2, FICTIF_3, FICTIF_4, FICTIF_5]
IDS = re.compile(r'\bid="([^"]+)"')
REFS_TO_IDS = re.compile(r'url\(#([^)]+)\)')


def _chart(ref):
    return build_chart(local_to_utc(ref["local"], ref["tz"]).utc)


@pytest.mark.parametrize("skin", list(SKINS))
@pytest.mark.parametrize("i", range(1, 6))
def test_svg_identical_apart_from_ids(i, skin):
    """Les cartes de tests/golden/fictif-*.svg sont écrites sans préfixe d'identifiant.
    Une fois les préfixes retirés, le SVG doit leur être identique à l'octet près :
    ni les préfixes ni une autre modification n'ont changé le rendu."""
    svg = render_bodygraph(_chart(REFS[i - 1]), skin=skin, name=f"Fictif {i} & <test>", uid="hdtest0001")
    stripped = svg.replace('id="hdtest0001-', 'id="').replace("url(#hdtest0001-", "url(#")
    assert stripped == (GOLDEN / f"fictif-{i}-{skin}.svg").read_text(encoding="utf-8")


@pytest.mark.parametrize("skin", list(SKINS))
def test_two_cards_share_no_id(skin):
    c = _chart(FICTIF_1)
    a, b = render_bodygraph(c, skin=skin), render_bodygraph(c, skin=skin)  # même thème, deux fois
    ids_a, ids_b = set(IDS.findall(a)), set(IDS.findall(b))
    assert ids_a and ids_b
    assert not ids_a & ids_b


@pytest.mark.parametrize("skin", list(SKINS))
def test_every_reference_points_to_an_id_of_the_same_card(skin):
    svg = render_bodygraph(_chart(FICTIF_1), skin=skin)
    ids = IDS.findall(svg)
    assert len(ids) == len(set(ids))              # pas de doublon dans une carte
    assert set(REFS_TO_IDS.findall(svg)) <= set(ids)  # aucun url(#…) orphelin
