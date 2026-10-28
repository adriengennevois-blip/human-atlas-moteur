# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Composite de deux personnes : chaque canal de l'ensemble et son type de connexion.

  électromagnétique : chacun a une porte du canal (et aucun n'a le canal seul) ;
  compromis         : l'un a le canal complet, l'autre une seule de ses portes ;
  dominance         : l'un a le canal complet, l'autre aucune de ses portes ;
  compagnonnage     : tous les deux ont le canal complet.
"""
from html import escape

from . import data as D
from .bodygraph import EXTRA_SKINS, PAGE_W, OFFSET, _xml_text, new_uid, render_bodygraph
from .chart import analyse

CONNECTIONS_FR = {"electromagnetic": "électromagnétique", "compromise": "compromis",
                  "dominance": "dominance", "companionship": "compagnonnage"}


def connection(channel: tuple[int, int], gates_a: set, gates_b: set) -> dict:
    """Type de connexion d'un canal présent dans la composite."""
    x, y = channel
    a, b = {x, y} & gates_a, {x, y} & gates_b
    full_a, full_b = len(a) == 2, len(b) == 2
    holder = None
    if full_a and full_b:
        kind = "companionship"
    elif full_a or full_b:
        holder = "a" if full_a else "b"
        kind = "compromise" if len(b if full_a else a) == 1 else "dominance"
    else:
        kind = "electromagnetic"
    return {"channel": f"{x}-{y}", "connection": kind, "connection_fr": CONNECTIONS_FR[kind],
            "gates": {"a": sorted(a), "b": sorted(b)}, "holder": holder}


def composite(chart_a, chart_b) -> dict:
    ga, gb = set(chart_a.active_gates), set(chart_b.active_gates)
    channels, defined, ctype, _authority, definition = analyse(ga | gb)
    rows = [connection(c, ga, gb) for c in channels]
    alone = set(chart_a.defined_centers) | set(chart_b.defined_centers)
    return {
        "type": ctype,
        "type_fr": D.TYPES_FR[ctype][0],
        "definition": definition,
        "definition_fr": D.DEFINITION_FR[definition],
        "defined_centers": defined,
        "centers_only_together": [c for c in defined if c not in alone],
        "channels": rows,
        "channels_only_together": [r["channel"] for r in rows if r["connection"] == "electromagnetic"],
    }


def composite_active_gates(chart_a, chart_b) -> dict:
    """Portes de la composite, au format du dessin : la personne A prend la place du
    côté « design », la personne B celle du côté « personality » (habillage composite)."""
    out = {}
    for g in chart_a.active_gates:
        out.setdefault(g, []).append("design")
    for g in chart_b.active_gates:
        out.setdefault(g, []).append("personality")
    return out


def render_composite(chart_a, chart_b, name_a: str = "", name_b: str = "", uid: str | None = None) -> str:
    """Carte SVG de la composite : même gabarit, une couleur par personne."""
    uid = uid or new_uid()
    s = EXTRA_SKINS["composite"]
    svg = render_bodygraph(active_gates=composite_active_gates(chart_a, chart_b), skin="composite",
                           show_planets=False, show_caption=False, uid=uid)
    na, nb = _xml_text(name_a or "Personne 1"), _xml_text(name_b or "Personne 2")
    c = composite(chart_a, chart_b)
    cx, y = PAGE_W / 2, 700 + OFFSET[1]
    title_len = len(name_a or "Personne 1") + len(name_b or "Personne 2") + 3
    size = 30 if title_len <= 28 else max(16, round(30 * 28 / title_len, 1))
    n_em = len(c["channels_only_together"])
    line = f"Composite : {c['type_fr']} · {D.DEFINITION_FR[c['definition']].lower()}"
    if n_em:
        line += f" · {n_em} {'canaux électromagnétiques' if n_em > 1 else 'canal électromagnétique'}"
    caption = "\n  ".join([
        f'<text x="{cx}" y="{y}" font-family="{s["font_title"]}" font-style="italic" font-size="{size:g}" '
        f'text-anchor="middle"><tspan fill="{s["design"]}">{na}</tspan>'
        f'<tspan fill="{s["text"]}"> &amp; </tspan><tspan fill="{s["personality"]}">{nb}</tspan></text>',
        f'<defs><linearGradient id="{uid}-filet" x1="0" x2="1"><stop offset="0" stop-color="{s["design"]}"/>'
        f'<stop offset="1" stop-color="{s["personality"]}"/></linearGradient></defs>'
        f'<rect x="{cx - 28}" y="{y + 14}" width="56" height="2" rx="1" fill="url(#{uid}-filet)"/>',
        f'<text x="{cx}" y="{y + 40}" font-family="{s["font_text"]}" font-size="16" text-anchor="middle" '
        f'fill="{s["text"]}">{escape(line)}</text>',
        f'<text x="{cx}" y="{y + 66}" font-family="{s["font_text"]}" font-style="italic" font-weight="300" '
        f'font-size="11.5" text-anchor="middle" fill="{s["muted"]}"><tspan fill="{s["design"]}">{na}</tspan>'
        f'  ·  <tspan fill="{s["personality"]}">{nb}</tspan>  ·  rayé ou demi-pastille : vous deux</text>',
    ])
    return svg[: svg.rindex("</svg>")] + caption + "\n  </svg>"
