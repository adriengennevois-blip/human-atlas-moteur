# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Le dessin doit dire exactement la même chose que le moteur."""
import re

from hd.bodygraph import SKINS, derive, render_bodygraph, validate_template

# Référence 1, relevée sur HumanDesignApp (porte : côtés activés)
REFERENCE_1_CAPTURE = {}


def test_template_matches_engine_tables():
    assert validate_template()


def test_reference_1_channels_and_centers():
    _, channels, defined = derive(REFERENCE_1_CAPTURE)
    assert channels == [(3, 60), (13, 33), (24, 61)]
    assert defined == {"head", "ajna", "throat", "g", "sacral", "root"}


def test_half_channel_colors_follow_the_code():
    svg = render_bodygraph(active_gates=REFERENCE_1_CAPTURE, skin="atlas", show_planets=False, show_caption=False)
    s = SKINS["atlas"]
    strokes = lambda g: set(re.findall(rf'class="gate-{g}" d="[^"]+" stroke="([^"]+)"', svg))
    assert strokes(24) == {s["design"]}            # 24 : Design seul → rouge
    assert strokes(61) == {s["personality"]}       # 61 : Personnalité seule → noir
    assert strokes(13) == {s["design"], s["personality"]}  # 13 : les deux → rayé
    assert 'class="gate-13"' in svg and "stroke-dasharray" in svg
    assert "gate-14" not in svg                    # porte inactive : aucun demi-canal coloré


def test_open_centers_stay_white():
    svg = render_bodygraph(active_gates=REFERENCE_1_CAPTURE, skin="classique", show_planets=False, show_caption=False)
    for center in ("spleen", "heart", "solar_plexus"):
        assert re.search(rf'id="hd[0-9a-f]{{8}}-center-{center}" d="[^"]+" fill="#ffffff"', svg)


def test_engine_matches_reference_1_capture():
    """Contrôle croisé : la référence 1 calculée par le moteur correspond à la capture HumanDesignApp."""
    from hd.chart import build_chart
    from hd.timeutil import local_to_utc

    from .test_reference import REFERENCE_1

    c = build_chart(local_to_utc(REFERENCE_1["local"], REFERENCE_1["tz"]).utc)
    assert (c.type, c.authority, c.profile) == ("Generator", "Sacral", "5/1")
    assert c.cross.startswith("Left Angle Cross of the Plane")
    assert {g: sorted(s) for g, s in c.active_gates.items()} == {g: sorted(s) for g, s in REFERENCE_1_CAPTURE.items()}
