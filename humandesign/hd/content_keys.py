# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Clés de contenu : un identifiant stable pour chaque élément d'un thème.

Les textes d'interprétation ne sont PAS dans ce dépôt public : ils appartiennent à
l'enseignant et vivent ailleurs. Le moteur ne fournit que les clés, par exemple :

  type.generator · authority.sacral · profile.5-1 · definition.triple-split
  center.throat.defined · center.throat.open · gate.24 · gate.24.line.6
  channel.24-61 · cross.left-angle.plane.2 · variable.determination.right
  variable.determination.color-3

Écriture : minuscules, mots séparés par « - », niveaux séparés par « . ».
Une clé publiée ne change plus jamais (les textes y sont rattachés).

    python -m hd.content_keys > content-keys.json    (depuis humandesign/)
"""
import json
import re
import sys
import unicodedata

from . import data as D

VARIABLES = {  # flèche → (côté, corps)
    "determination": ("design", "sun"),
    "environment": ("design", "north_node"),
    "motivation": ("personality", "sun"),
    "perspective": ("personality", "north_node"),
}
DEFINITION_SLUGS = {0: "none", 1: "single", 2: "split", 3: "triple-split", 4: "quadruple-split"}
PROFILES = ["1/3", "1/4", "2/4", "2/5", "3/5", "3/6", "4/6", "4/1", "5/1", "5/2", "6/2", "6/3"]


def slug(text: str) -> str:
    """« Manifesting Generator » → manifesting-generator, « Self-Projected » → self-projected."""
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def _cross_name(name: str) -> str:
    """« the Plane » → plane (l'article anglais n'entre pas dans la clé)."""
    return slug(re.sub(r"^the\s+", "", name, flags=re.I))


def _quarter(gate: int) -> int:
    return (D.GATE_ORDER.index(gate) - 2) % 64 // 16  # même calcul que hd.chart


def cross_key(personality_sun_gate: int, profile: str) -> str:
    """Clé de la croix d'incarnation, dérivée comme hd.chart.build_chart nomme la croix."""
    pl = int(profile.split("/")[0])
    q = _quarter(personality_sun_gate)
    if profile == "4/1":
        return f"cross.juxtaposition.{_cross_name(D.JUXTAPOSITION_CROSSES[personality_sun_gate])}"
    if pl >= 5:
        return f"cross.left-angle.{_cross_name(D.LAX_BY_GATE[personality_sun_gate])}.{1 if q < 2 else 2}"
    return f"cross.right-angle.{_cross_name(D.RAX_BY_GATE[personality_sun_gate])}.{q + 1}"


def chart_keys(chart) -> dict:
    """Les clés de contenu d'un thème, rangées par catégorie."""
    acts = list(chart.personality.values()) + list(chart.design.values())
    defined = set(chart.defined_centers)
    arrows = {"design_sun": "determination", "design_node": "environment",
              "personality_sun": "motivation", "personality_node": "perspective"}
    directions = {arrows[k]: ("left" if v == "gauche" else "right") for k, v in chart.variables.items()}
    return {
        "type": f"type.{slug(chart.type)}",
        "authority": f"authority.{slug(chart.authority)}",
        "profile": f"profile.{chart.profile.replace('/', '-')}",
        "definition": f"definition.{DEFINITION_SLUGS[chart.definition]}",
        "cross": cross_key(chart.personality["sun"].gate, chart.profile),
        "centers": [f"center.{slug(c)}.{'defined' if c in defined else 'open'}" for c in D.CENTERS],
        "gates": [f"gate.{g}" for g in sorted({a.gate for a in acts})],
        "lines": [f"gate.{g}.line.{l}" for g, l in sorted({(a.gate, a.line) for a in acts})],
        "channels": [f"channel.{a}-{b}" for a, b in chart.channels],
        "variables": [k for name, (side, planet) in VARIABLES.items()
                      for k in (f"variable.{name}.{directions[name]}",
                                f"variable.{name}.color-{getattr(chart, side)[planet].color}")],
    }


def all_keys() -> dict:
    """Toutes les clés possibles, par catégorie, dans un ordre stable."""
    gates = sorted(D.GATE_ORDER)
    crosses = sorted({cross_key(g, p) for g in gates for p in PROFILES})
    return {
        "type": [f"type.{slug(t)}" for t in D.TYPES_FR],
        "authority": [f"authority.{slug(a)}" for a in D.AUTHORITY_FR],
        "profile": [f"profile.{p.replace('/', '-')}" for p in PROFILES],
        "definition": [f"definition.{s}" for s in DEFINITION_SLUGS.values()],
        "center": [f"center.{slug(c)}.{state}" for c in D.CENTERS for state in ("defined", "open")],
        "gate": [f"gate.{g}" for g in gates],
        "line": [f"gate.{g}.line.{l}" for g in gates for l in range(1, 7)],
        "channel": [f"channel.{a}-{b}" for a, b in D.CHANNELS],
        "cross": crosses,
        "variable": [f"variable.{v}.{x}" for v in VARIABLES
                     for x in ("left", "right", *(f"color-{c}" for c in range(1, 7)))],
    }


def manifest() -> dict:
    keys = all_keys()
    return {
        "version": 1,
        "description": "Liste de toutes les clés de contenu du moteur Human Design de Human Atlas. "
                       "Une clé publiée ne change plus : les textes y sont rattachés.",
        "counts": {k: len(v) for k, v in keys.items()} | {"total": sum(len(v) for v in keys.values())},
        "keys": keys,
    }


if __name__ == "__main__":
    json.dump(manifest(), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
