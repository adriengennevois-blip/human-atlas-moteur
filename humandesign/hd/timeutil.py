# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from timezonefinder import TimezoneFinder

_tf = TimezoneFinder()

GEOCODER_TIMEOUT = 10  # secondes (le défaut de geopy, 1 s, échoue souvent)


class GeocodingUnavailable(ValueError):
    """Le service de géocodage ne répond pas (réseau, délai dépassé, quota)."""


@dataclass
class Place:
    name: str
    lat: float
    lon: float
    tz: str
    # Autres lieux du même nom situés dans un AUTRE fuseau horaire : le thème
    # pourrait être faux si la personne voulait dire l'un d'eux.
    alternatives: list = field(default_factory=list)


@dataclass
class ResolvedTime:
    local: datetime
    utc: datetime
    utc_offset_hours: float
    dst: bool
    warning: str | None = None


def _search(query: str) -> list[tuple[str, float, float]]:
    """Interroge OpenStreetMap (Nominatim) : jusqu'à 5 résultats (adresse, lat, lon)."""
    from geopy.geocoders import Nominatim

    res = Nominatim(user_agent="hd-bodygraph-engine", timeout=GEOCODER_TIMEOUT).geocode(
        query, exactly_one=False, limit=5, language="fr")
    return [(r.address, r.latitude, r.longitude) for r in res or []]


def geocode(query: str) -> Place:
    from geopy.exc import GeopyError

    try:
        results = _search(query)
    except GeopyError as e:
        raise GeocodingUnavailable(f"Géocodage impossible ({e.__class__.__name__}) : utiliser --lat/--lon") from e
    if not results:
        raise ValueError(f"Lieu introuvable : {query!r}")
    name, lat, lon = results[0]
    tz = timezone_at(lat, lon)
    alternatives = []
    for other, olat, olon in results[1:]:
        try:
            otz = timezone_at(olat, olon)
        except ValueError:
            continue
        label = f"{other} ({otz})"
        if otz != tz and label not in alternatives:
            alternatives.append(label)
    return Place(name, lat, lon, tz, alternatives)


def timezone_at(lat: float, lon: float) -> str:
    tz = _tf.timezone_at(lat=lat, lng=lon)
    if tz is None:
        raise ValueError(f"Aucun fuseau horaire pour {lat}, {lon}")
    return tz


def _utc_label(dt: datetime) -> str:
    h = dt.utcoffset().total_seconds() / 3600
    return f"UTC{h:+g}"


def local_to_utc(naive: datetime, tz_name: str, fold: int = 0) -> ResolvedTime:
    """Convert a civil birth time to UTC using the IANA historical tz database
    (DST rules, war time, pre-standardisation LMT offsets)."""
    tz = ZoneInfo(tz_name)
    a = naive.replace(tzinfo=tz, fold=0)
    b = naive.replace(tzinfo=tz, fold=1)
    local = naive.replace(tzinfo=tz, fold=fold)
    warning = None
    if a.utcoffset() != b.utcoffset():
        roundtrip = a.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None)
        if roundtrip != naive:
            when = "d'après" if fold else "d'avant"
            warning = ("Heure inexistante (sautée au changement d'heure) : calculée comme "
                       f"si elle avait été notée à l'heure {when} le changement ({_utc_label(local)}).")
        else:
            which = "2e" if fold else "1re"
            warning = ("Heure ambiguë (elle a existé deux fois au changement d'heure) : "
                       f"{which} occurrence retenue ({_utc_label(local)}).")
    utc = local.astimezone(timezone.utc)
    return ResolvedTime(
        local=local,
        utc=utc,
        utc_offset_hours=local.utcoffset().total_seconds() / 3600,
        dst=bool(local.dst()),
        warning=warning,
    )
