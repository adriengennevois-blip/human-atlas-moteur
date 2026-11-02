# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Fiche de lecture : des DONNÉES structurées, une entrée par rubrique.

Chaque entrée a un identifiant stable (« digestion.color », « environment.tone », « channels »…)
auquel le site rattache les textes d'Adrien. Le moteur ne contient AUCUN texte d'interprétation :
seulement des données (numéros, clés) et des noms courts (hd/variables_fr.py, hd/reading_fr.py :
à valider par Adrien).

Deux rubriques n'ont volontairement aucun calcul : « relations.me_vs_others » (des statistiques
viendront plus tard) et « sleep.rhythm » (les règles viendront d'Adrien) ; elles ne renvoient
que des données brutes et un identifiant.
"""
from . import data as D
from . import precision as P
from . import reading_fr as R
from . import variables_fr as VF
from .signup import _profile_label

VERSION = 1


def _named(key: str, name: str) -> dict:
    return {"key": key, "name": name}


def _centers(chart) -> tuple[list, list]:
    defined = [c for c in D.CENTERS if c in chart.defined_centers]
    return ([_named(c, D.CENTER_NAMES_FR[c]) for c in defined],
            [_named(c, D.CENTER_NAMES_FR[c]) for c in D.CENTERS if c not in defined])


def _cross(chart) -> dict:
    angle = ("juxtaposition" if chart.cross.startswith("Juxtaposition")
             else "left-angle" if chart.cross.startswith("Left") else "right-angle")
    p, d = chart.personality, chart.design
    return {"name": chart.cross, "angle": _named(angle, R.CROSS_ANGLES_FR[angle]),
            "quarter": chart.meta.get("quarter"), "gates_label": chart.cross_gates,
            "gates": {"personality_sun": p["sun"].gate, "personality_earth": p["earth"].gate,
                      "design_sun": d["sun"].gate, "design_earth": d["earth"].gate}}


def _channels(chart) -> list:
    rows = []
    for a, b in chart.channels:
        key = (min(a, b), max(a, b))
        group, circuit = R.CHANNEL_CIRCUITS[key]
        rows.append({"id": f"channel.{key[0]}-{key[1]}", "channel": f"{key[0]}-{key[1]}",
                     "gates": list(key), "name": R.CHANNEL_NAMES_FR[key],
                     "circuit_group": _named(group, R.CIRCUIT_GROUPS_FR[group]),
                     "circuit": _named(circuit, R.CIRCUITS_FR[circuit])})
    return rows


def _entry(id_: str, section: str, title: str, value) -> dict:
    return {"id": id_, "section": section, "title": title, "value": value}


def _variable_entries(chart) -> list:
    out = []
    for name, v in P.variables(chart).items():
        rid, title = VF.READING_IDS[name], VF.ARROW_TITLES[name]
        part = lambda k: f"{title} · {VF.PART_NAMES_FR[k]}"
        orient = v["orientation"]
        out.append(_entry(f"{rid}.orientation", "variables", part("orientation"),
                          {"key": orient, "name": VF.ORIENTATION_NAMES_FR[orient], "direction": v["direction"]}))
        color = {"number": v["color"], "name": v["color_name"]}
        if "opposite_color_name" in v:  # Motivation et Perspective : pas de sous-catégorie, une couleur opposée
            color["opposite_name"] = v["opposite_color_name"]
        out.append(_entry(f"{rid}.color", "variables", part("color"), color))
        out.append(_entry(f"{rid}.tone", "variables", part("tone"), {"number": v["tone"], "name": v["tone_name"]}))
        if "color_side" in v:  # Digestion et Environnement : sous-catégorie qui découle du ton
            out.append(_entry(f"{rid}.subcategory", "variables", part("subcategory"),
                              {"name": v["color_side"], "from_color": v["color"], "from_tone": v["tone"]}))
        out.append(_entry(f"{rid}.base", "variables", part("base"), {"number": v["base"]}))
    return out


def reading(chart) -> dict:
    """La fiche de lecture d'un thème : {"version", "entries": [...], "to_validate": [...]}."""
    t_fr, strategy, signature, not_self = D.TYPES_FR[chart.type]
    defined, open_ = _centers(chart)
    type_ = _named(chart.type, t_fr)
    entries = [
        _entry("channels", "channels", R.SECTION_NAMES_FR["channels"],
               {"count": len(chart.channels), "channels": _channels(chart)}),
        _entry("type", "other", "Type", type_),
        _entry("strategy", "other", "Stratégie", {"name": strategy}),
        _entry("authority", "other", "Autorité", _named(chart.authority, D.AUTHORITY_FR[chart.authority])),
        _entry("profile", "other", "Profil",
               {"key": chart.profile, "personality_line": int(chart.profile[0]), "design_line": int(chart.profile[-1]),
                "name": _profile_label(chart.profile)}),
        _entry("definition", "other", "Définition", {"number": chart.definition, "name": D.DEFINITION_FR[chart.definition]}),
        _entry("cross", "other", "Croix d'incarnation", _cross(chart)),
        _entry("signature", "other", "Signature", {"name": signature}),
        _entry("not_self_theme", "other", "Thème du non-soi", {"name": not_self}),
        _entry("centers.defined", "other", "Centres définis", defined),
        _entry("centers.open", "other", "Centres ouverts", open_),
        *_variable_entries(chart),
        {"id": "relations.me_vs_others", "section": "relations", "title": R.RUBRICS_FR["relations.me_vs_others"],
         "status": "pending_statistics",
         "value": {"type": type_, "profile": chart.profile, "defined_centers": defined, "open_centers": open_}},
        {"id": "sleep.rhythm", "section": "sleep", "title": R.RUBRICS_FR["sleep.rhythm"], "status": "pending_rules",
         "value": {"type": type_, "aura": {"name": R.AURA_FR[chart.type]},
                   "defined_centers": defined, "open_centers": open_}},
    ]
    to_validate = ["channels (noms et circuits)", "cross.angle", "sleep.rhythm.aura"] + \
                  [f"{VF.READING_IDS[v]}.tone (nom du ton)" for v in VF.TONE_NAME_TO_VALIDATE]
    return {"version": VERSION, "entries": entries, "to_validate": to_validate}
