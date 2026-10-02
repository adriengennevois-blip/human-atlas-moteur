# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""
Résumé Human Design pour l'inscription.

Objectif : donner à une personne son Type, son Autorité et son Profil dès
qu'elle s'inscrit — sans dépendre du rendu SVG (hd.svg n'est pas importé ici).
Croix d'incarnation et Canaux sont disponibles en option (extended=True),
pour un futur retour plus détaillé, sans changer la forme de base.

Ce module ne réécrit aucun calcul : il appelle hd.chart.build_chart, le même
moteur validé sur les 5 thèmes de référence (tests/test_reference.py).
"""

from dataclasses import dataclass
from datetime import datetime

from . import data as D
from .chart import build_chart
from .timeutil import local_to_utc, timezone_at


class SignupInputError(ValueError):
    """Entrée invalide : ni birth_utc, ni (date + time + (tz ou lat/lon))."""


def _profile_label(profile: str) -> str:
    a, b = (int(x) for x in profile.split("/"))
    return f"{profile} ({D.LINE_NAMES_FR[a]} / {D.LINE_NAMES_FR[b]})"


def resolve_birth_utc(
    *,
    date: str | None = None,
    time: str | None = None,
    tz: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    fold: int = 0,
    birth_utc: datetime | None = None,
) -> tuple[datetime, str | None]:
    """Renvoie (datetime UTC, avertissement éventuel sur l'heure locale).

    Deux façons de fournir la naissance :
      - birth_utc déjà connu (le formulaire a déjà normalisé en UTC) ;
      - date="AAAA-MM-JJ" + time="HH:MM"[:SS] + tz="Europe/Paris"
        (ou lat/lon pour déduire le fuseau — nécessite timezonefinder).
    """
    if birth_utc is not None:
        return birth_utc, None
    if date is None or time is None:
        raise SignupInputError("fournir birth_utc, ou date + time (+ tz ou lat/lon)")
    t = time if time.count(":") == 2 else time + ":00"
    naive = datetime.fromisoformat(f"{date}T{t}")
    if tz is None:
        if lat is None or lon is None:
            raise SignupInputError("fournir tz, ou lat + lon")
        tz = timezone_at(lat, lon)
    rt = local_to_utc(naive, tz, fold)
    return rt.utc, rt.warning


def signup_result(
    *,
    date: str | None = None,
    time: str | None = None,
    tz: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    fold: int = 0,
    birth_utc: datetime | None = None,
    extended: bool = False,
) -> dict:
    """Calcule le résultat HD à afficher à l'inscription.

    Retourne toujours :
      type, type_fr, authority, authority_fr, profile, profile_label,
      birth_utc (iso), time_warning (str ou None)

    Si extended=True, ajoute :
      cross, cross_gates, channels (liste "a-b"), defined_centers, definition
    """
    resolved_utc, warning = resolve_birth_utc(
        date=date, time=time, tz=tz, lat=lat, lon=lon, fold=fold, birth_utc=birth_utc
    )
    c = build_chart(resolved_utc)

    out = {
        "type": c.type,
        "type_fr": D.TYPES_FR[c.type][0],
        "authority": c.authority,
        "authority_fr": D.AUTHORITY_FR[c.authority],
        "profile": c.profile,
        "profile_label": _profile_label(c.profile),
        "birth_utc": c.birth_utc.isoformat(),
        "time_warning": warning,
    }
    if extended:
        out.update(
            {
                "cross": c.cross,
                "cross_gates": c.cross_gates,
                "channels": [f"{a}-{b}" for a, b in c.channels],
                "defined_centers": c.defined_centers,
                "definition": c.definition,
            }
        )
    return out
