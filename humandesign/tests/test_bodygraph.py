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

# Thème fictif 1 (tests/test_reference.py), porte : côtés activés. La vérification sur une
# capture de HumanDesignApp se fait sur un thème réel, hors dépôt (test_private_references_match_app).
FICTIF_1_GATES = {
    4: ["design"], 5: ["design"], 9: ["personality"], 10: ["design", "personality"],
    11: ["personality"], 13: ["personality"], 14: ["personality"], 19: ["design"], 22: ["design"],
    24: ["design", "personality"], 26: ["personality"], 28: ["design", "personality"],
    34: ["personality"], 43: ["design"], 44: ["design", "personality"], 45: ["personality"],
    46: ["design"], 47: ["design"], 50: ["personality"], 59: ["design"], 64: ["design"],
}


def test_template_matches_engine_tables():
    assert validate_template()


def test_fictif_1_channels_and_centers():
    _, channels, defined = derive(FICTIF_1_GATES)
    assert channels == [(10, 34), (26, 44), (47, 64)]
    assert defined == {"head", "ajna", "g", "heart", "sacral", "spleen"}


def test_half_channel_colors_follow_the_code():
    svg = render_bodygraph(active_gates=FICTIF_1_GATES, skin="atlas", show_planets=False, show_caption=False)
    s = SKINS["atlas"]
    strokes = lambda g: set(re.findall(rf'class="gate-{g}" d="[^"]+" stroke="([^"]+)"', svg))
    assert strokes(47) == {s["design"]}            # 47 : Design seul
    assert strokes(45) == {s["personality"]}       # 45 : Personnalité seule
    assert strokes(10) == {s["design"], s["personality"]}  # 10 : les deux → rayé
    assert 'class="gate-10"' in svg and "stroke-dasharray" in svg
    assert "gate-1\"" not in svg                    # porte inactive : aucun demi-canal coloré


def test_open_centers_stay_white():
    svg = render_bodygraph(active_gates=FICTIF_1_GATES, skin="classique", show_planets=False, show_caption=False)
    for center in ("throat", "solar_plexus", "root"):
        assert re.search(rf'id="hd[0-9a-f]{{8}}-center-{center}" d="[^"]+" fill="#ffffff"', svg)


def test_engine_matches_fictif_1():
    from hd.chart import build_chart
    from hd.timeutil import local_to_utc

    from .test_reference import FICTIF_1

    c = build_chart(local_to_utc(FICTIF_1["local"], FICTIF_1["tz"]).utc)
    assert {g: sorted(s) for g, s in c.active_gates.items()} == {g: sorted(s) for g, s in FICTIF_1_GATES.items()}
