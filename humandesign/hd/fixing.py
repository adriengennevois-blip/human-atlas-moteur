# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Line fixing (exaltation ▲ / detriment ▼ / juxtaposition ★).

A planet's line is fixed by its own entry in the table and by any planet
(personality or design) sitting in one of the gate's harmonic gates, evaluated
against *this* gate.line.
"""
import json
import os

with open(os.path.join(os.path.dirname(__file__), "fixing_table.json"), encoding="utf-8") as f:
    _DATA = json.load(f)

_BITS = {"E": 1, "D": 2, "J": 3}
_TABLE = {p: {k: _BITS[v] for k, v in lines.items()} for p, lines in _DATA["lines"].items()}
HARMONIC_GATES = {int(g): v for g, v in _DATA["harmonic_gates"].items()}
SYMBOLS = {0: "", 1: "▲", 2: "▼", 3: "★"}


def _state(planet: str, gate: int, line: int) -> int:
    return _TABLE.get(planet, {}).get(f"{gate}.{line}", 0)


def fixing(planet: str, act, all_acts: list) -> str:
    s = _state(planet, act.gate, act.line)
    harmonics = HARMONIC_GATES[act.gate]
    for other in all_acts:
        if other.gate in harmonics:
            s |= _state(other.planet, act.gate, act.line)
    return SYMBOLS[s]
