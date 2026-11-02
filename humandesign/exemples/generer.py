# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Génère les cartes des 5 thèmes de référence, dans les deux habillages, et la carte
d'exemple dans les deux thèmes de marque (atlas.svg, gdh.svg), avec et sans les flèches des
variables (atlas-variables.svg, gdh-variables.svg), puis avec un transit posé dessus (atlas-transit.svg,
gdh-transit.svg).

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

# Les mêmes cartes avec les quatre flèches des variables (show_variables) et leur titre (variable_labels).
for theme in ("atlas", "gdh"):
    svg = render_bodygraph(c, theme=theme, name="Exemple", uid="exemple",
                           show_variables=True, variable_labels=True)
    ElementTree.fromstring(svg)
    (here / f"{theme}-variables.svg").write_text(svg, encoding="utf-8")
    print(f"{theme}-variables.svg  OK ({len(svg) // 1024} Ko)")

# Le transit posé sur la carte (route /v1/transit/chart) : même personne fictive, instant fixe.
from datetime import timezone  # noqa: E402

from hd.timeline import transit_on_chart  # noqa: E402

AT = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
res = transit_on_chart(c, AT)
for theme in ("atlas", "gdh"):
    svg = render_bodygraph(
        c, theme=theme, name="Exemple", uid="exemple", transit_gates={g["gate"] for g in res["activates"]["gates"]},
        transit_centers=set(res["activates"]["centers_newly_defined"]),
        transit_note="transit du 02/11/2026 à 12:00 UTC")
    ElementTree.fromstring(svg)
    (here / f"{theme}-transit.svg").write_text(svg, encoding="utf-8")
    print(f"{theme}-transit.svg  OK ({len(svg) // 1024} Ko)")
