# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Génère les cartes des 5 thèmes de référence, dans les deux habillages, et la carte
d'exemple dans les deux thèmes de marque (atlas.svg, gdh.svg).

    python -m exemples.generer   (depuis le dossier humandesign/)
"""
from pathlib import Path
from xml.etree import ElementTree

from hd.bodygraph import SKINS, render_bodygraph
from hd.chart import build_chart
from hd.timeutil import local_to_utc
from tests.test_reference import FICTIF_1, FICTIF_4, FICTIFS

here = Path(__file__).parent
for i, ref in enumerate(FICTIFS, 1):
    c = build_chart(local_to_utc(ref["local"], ref["tz"]).utc)
    for skin in SKINS:
        slug = f"fictif-{i}-{skin}"
        svg = render_bodygraph(c, skin=skin, name=f"Fictif {i}", uid=slug)
        ElementTree.fromstring(svg)  # lève une erreur si le XML est invalide
        (here / f"{slug}.svg").write_text(svg, encoding="utf-8")
        print(f"{slug}.svg  OK ({len(svg) // 1024} Ko)")

# Composite des thèmes fictifs 1 et 4 (habillage « composite »).
from hd.composite import render_composite  # noqa: E402

charts = [build_chart(local_to_utc(r["local"], r["tz"]).utc) for r in (FICTIF_1, FICTIF_4)]
svg = render_composite(*charts, "Fictif 1", "Fictif 4", uid="composite-fictif-1-4")
ElementTree.fromstring(svg)
(here / "composite-fictif-1-4.svg").write_text(svg, encoding="utf-8")
print(f"composite-fictif-1-4.svg  OK ({len(svg) // 1024} Ko)")

# Les deux thèmes de marque, pour la même naissance (personne fictive : 1er janvier 2000, 12 h, Paris).
from datetime import datetime  # noqa: E402

c = build_chart(local_to_utc(datetime(2000, 1, 1, 12, 0), "Europe/Paris").utc)
for theme in ("atlas", "gdh"):
    svg = render_bodygraph(c, theme=theme, name="Exemple", uid="exemple")
    ElementTree.fromstring(svg)
    (here / f"{theme}.svg").write_text(svg, encoding="utf-8")
    print(f"{theme}.svg  OK ({len(svg) // 1024} Ko)")
