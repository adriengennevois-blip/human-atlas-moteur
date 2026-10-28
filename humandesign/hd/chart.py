# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

from dataclasses import dataclass, field, asdict
from datetime import datetime

from . import data as D
from .fixing import fixing
from .ephemeris import design_jd, jd_to_datetime, julian_day, positions


@dataclass
class Activation:
    planet: str
    longitude: float
    gate: int
    line: int
    color: int
    tone: int
    base: int
    fixing: str = ""

    @property
    def label(self) -> str:
        return f"{self.gate}.{self.line}{self.fixing}"


def activation(planet: str, lon: float) -> Activation:
    x = (lon - D.WHEEL_START) % 360
    idx = int(x // D.GATE_ARC)
    r = x - idx * D.GATE_ARC
    line = int(r // D.LINE_ARC)
    r -= line * D.LINE_ARC
    color = int(r // D.COLOR_ARC)
    r -= color * D.COLOR_ARC
    tone = int(r // D.TONE_ARC)
    r -= tone * D.TONE_ARC
    base = int(r // D.BASE_ARC)
    return Activation(planet, lon, D.GATE_ORDER[idx], min(line, 5) + 1,
                      min(color, 5) + 1, min(tone, 5) + 1, min(base, 4) + 1)


@dataclass
class Chart:
    name: str
    birth_utc: datetime
    design_utc: datetime
    personality: dict
    design: dict
    active_gates: dict = field(default_factory=dict)
    channels: list = field(default_factory=list)
    defined_centers: list = field(default_factory=list)
    type: str = ""
    authority: str = ""
    profile: str = ""
    definition: int = 0
    cross: str = ""
    cross_gates: str = ""
    variables: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["birth_utc"] = self.birth_utc.isoformat()
        d["design_utc"] = self.design_utc.isoformat()
        return d


def _components(nodes, edges):
    parent = {n: n for n in nodes}

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    for a, b in edges:
        parent[find(a)] = find(b)
    groups = {}
    for n in nodes:
        groups.setdefault(find(n), set()).add(n)
    return list(groups.values())


def _connected(a, b, edges):
    return any(a in comp and b in comp for comp in _components({x for e in edges for x in e}, edges))


def analyse(active_gates) -> tuple[list, list, str, str, int]:
    """Canaux, centres définis, type, autorité et définition d'un ensemble de portes actives
    (un thème, ou plusieurs thèmes réunis pour une composite)."""
    active = set(active_gates)
    channels = [(a, b) for a, b in D.CHANNELS if a in active and b in active]
    edges = [(D.GATE_CENTER[a], D.GATE_CENTER[b]) for a, b in channels]
    defined = sorted({c for e in edges for c in e}, key=list(D.CENTERS).index)

    motor_to_throat = any(_connected(m, "throat", edges) for m in D.MOTORS)
    if not defined:
        ctype = "Reflector"
    elif "sacral" in defined:
        ctype = "Manifesting Generator" if motor_to_throat else "Generator"
    elif motor_to_throat:
        ctype = "Manifestor"
    else:
        ctype = "Projector"

    if "solar_plexus" in defined:
        authority = "Emotional"
    elif "sacral" in defined:
        authority = "Sacral"
    elif "spleen" in defined:
        authority = "Splenic"
    elif "heart" in defined:
        authority = "Ego Manifested" if _connected("heart", "throat", edges) else "Ego Projected"
    elif "g" in defined:
        authority = "Self-Projected"
    elif defined:
        authority = "Mental"
    else:
        authority = "Lunar"

    definition = len(_components(set(defined), edges))
    return channels, defined, ctype, authority, definition


def build_chart(birth_utc: datetime, name: str = "", meta: dict | None = None) -> Chart:
    jd_p = julian_day(birth_utc)
    jd_d = design_jd(jd_p)
    pos_p, pos_d = positions(jd_p), positions(jd_d)
    pers = {p: activation(p, pos_p[p]) for p in D.PLANETS}
    des = {p: activation(p, pos_d[p]) for p in D.PLANETS}
    everything = list(pers.values()) + list(des.values())
    for a in everything:
        a.fixing = fixing(a.planet, a, everything)

    active = {}
    for side, acts in (("personality", pers), ("design", des)):
        for a in acts.values():
            active.setdefault(a.gate, set()).add(side)

    channels, defined, ctype, authority, definition = analyse(active)

    pl, dl = pers["sun"].line, des["sun"].line
    profile = f"{pl}/{dl}"
    ps = pers["sun"].gate
    quarter = (D.GATE_ORDER.index(ps) - 2) % 64 // 16
    gates = f"{ps}/{pers['earth'].gate} | {des['sun'].gate}/{des['earth'].gate}"
    if profile == "4/1":
        cross = f"Juxtaposition Cross of {D.JUXTAPOSITION_CROSSES[ps]}"
    elif pl >= 5:
        cross = f"Left Angle Cross of {D.LAX_BY_GATE[ps]} {1 if quarter < 2 else 2}"
    else:
        cross = f"Right Angle Cross of {D.RAX_BY_GATE[ps]} {quarter + 1}"

    arrow = lambda a: "gauche" if a.tone <= 3 else "droite"
    variables = {
        "design_sun": arrow(des["sun"]),
        "design_node": arrow(des["north_node"]),
        "personality_sun": arrow(pers["sun"]),
        "personality_node": arrow(pers["north_node"]),
    }

    return Chart(
        name=name, birth_utc=birth_utc, design_utc=jd_to_datetime(jd_d),
        personality=pers, design=des,
        active_gates={g: sorted(s) for g, s in sorted(active.items())},
        channels=channels, defined_centers=defined, type=ctype, authority=authority,
        profile=profile, definition=definition, cross=cross, cross_gates=gates,
        variables=variables, meta={**(meta or {}), "quarter": D.QUARTERS[quarter]},
    )


def summary_fr(c: Chart) -> list[str]:
    t, strat, sig, notself = D.TYPES_FR[c.type]
    pl, dl = (int(x) for x in c.profile.split("/"))
    return [
        f"Type : {t}",
        f"Stratégie : {strat}",
        f"Autorité : {D.AUTHORITY_FR[c.authority]}",
        f"Profil : {c.profile} ({D.LINE_NAMES_FR[pl]} / {D.LINE_NAMES_FR[dl]})",
        f"Définition : {D.DEFINITION_FR[c.definition]}",
        f"Croix d'incarnation : {c.cross} ({c.cross_gates})",
        f"Signature : {sig}  ·  Thème du non-soi : {notself}",
    ]
