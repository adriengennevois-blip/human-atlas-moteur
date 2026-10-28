# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Groupes (3 à 5 personnes) : composite du groupe, qui apporte quoi, connexions deux à deux.

Les personnes sont numérotées à partir de 1, dans l'ordre de la requête.

La Penta (ses canaux, ses rôles, le passage à un groupe plus large) n'est PAS calculée :
ses règles doivent être fournies par l'enseignant avant toute ligne de code. penta()
renvoie seulement l'état « en attente de règles ».
"""
from itertools import combinations

from .chart import analyse
from .composite import composite

MIN_PEOPLE, MAX_PEOPLE = 3, 5


def group(charts: list) -> dict:
    gates_of = [set(c.active_gates) for c in charts]
    channels, defined, *_ = analyse(set().union(*gates_of))
    alone = set().union(*(c.defined_centers for c in charts))
    rows = []
    for x, y in channels:
        holders = [i for i, g in enumerate(gates_of, 1) if {x, y} <= g]
        rows.append({
            "channel": f"{x}-{y}",
            # pour chaque porte du canal : les personnes qui l'apportent
            "gates": {str(g): [i for i, gs in enumerate(gates_of, 1) if g in gs] for g in (x, y)},
            "holders": holders,                 # personnes qui ont le canal complet
            "only_together": not holders,       # personne ne l'a seule : il naît du groupe
        })
    return {
        "size": len(charts),
        "defined_centers": defined,
        "centers_only_together": [c for c in defined if c not in alone],
        "channels": rows,
        "channels_only_together": [r["channel"] for r in rows if r["only_together"]],
        "pairs": [{"people": [i + 1, j + 1], **composite(charts[i], charts[j])}
                  for i, j in combinations(range(len(charts)), 2)],
        "penta": penta(charts),
    }


def penta(charts: list) -> dict:
    """Structure réservée. À coder seulement avec les règles exactes de l'enseignant :
    canaux de la Penta, rôle de chaque canal ou porte, traitement des « trous » et des
    porte(s) apportées par plusieurs personnes, seuil et règles du groupe plus large."""
    return {"status": "pending_rules", "message": "Penta : en attente des règles de l'enseignant."}
