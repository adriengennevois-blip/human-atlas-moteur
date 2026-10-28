# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""
API du moteur Human Design de Human Atlas.

L'app real-world-weavers appelle ce moteur côté serveur (jamais depuis le
navigateur : la clé doit rester secrète).

  GET  /            → « ok »
  GET  /source      → adresse du code source public (obligation de l'AGPL)
  POST /v1/transit  → transits d'un instant (+ superposition avec un thème natal)
  GET  /v1/transits/day?date=AAAA-MM-JJ&tz=Europe/Paris → changements de porte et de ligne du jour
  POST /v1/return   → retours (solaire, Saturne, Chiron, opposition d'Uranus) d'une année
  POST /v1/dream    → thème de rêve : 501, en attente de spécification
  POST /v1/group    → groupe de 3 à 5 personnes (qui apporte quoi, paires ; Penta en attente)
  POST /v1/composite → composite de deux personnes (connexions canal par canal, + SVG)
  POST /v1/chart    → thème calculé (+ SVG du bodygraph ; « details »: true ajoute
                      couleur/ton/base, sensibilité à l'heure, variables, précision)

Application WSGI sans framework : tourne telle quelle sur o2switch
(cPanel → « Setup Python App », via passenger_wsgi.py).

Réglages (variables d'environnement, à saisir dans cPanel) :
  ENGINE_API_KEY   clé partagée avec l'app (au moins 32 caractères)
  TRANSITS_API_KEY facultative : clé qui n'ouvre que la vue du jour des transits
                   (GET /v1/transits/day), sans accès aux calculs de naissance
  SOURCE_URL       adresse du dépôt public du moteur, renvoyée par GET /source

Données personnelles : rien n'est écrit sur disque ni dans les journaux.
Le moteur calcule, répond, puis oublie.
"""

import hmac
import json
import logging
import math
import os
import re
from datetime import date as Date, datetime, timezone
from urllib.parse import parse_qs
from zoneinfo import available_timezones

from hd import data as D
from hd import precision as P
from hd.bodygraph import SKINS, render_bodygraph, summary_sentence, validate_template
from hd.themes import PUBLIC_THEMES
from hd.chart import build_chart
from hd.composite import composite, render_composite
from hd.content_keys import chart_keys
from hd.group import MAX_PEOPLE, MIN_PEOPLE, group
from hd.returns import RETURNS, find_returns, years_with_returns
from hd.transit import day_changes, overlay, transit
from hd.signup import _profile_label
from hd.timeutil import GeocodingUnavailable, geocode, local_to_utc, timezone_at

log = logging.getLogger("hd-api")

MAX_BODY = 10 * 1024
MIN_KEY_LENGTH = 32
# Les fichiers d'éphémérides couvrent 1800-2400 ; le Design remonte ~88 jours avant.
MIN_YEAR, MAX_YEAR = 1801, 2399
PRECISIONS = ("exacte", "approximative", "inconnue")
FIELDS = {"date", "time", "time_precision", "tz", "lat", "lon", "place", "name", "skin", "theme", "include_svg", "details", "content_keys"}
MAX_NAME = 60
MAX_PLACE = 200

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_TIME_RE = re.compile(r"\d{2}:\d{2}")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f\ud800-\udfff]")  # contrôles et demi-caractères Unicode
_TIMEZONES = available_timezones()
validate_template()  # au démarrage : le 1er appel ne paie pas cette vérification


class ApiError(Exception):
    def __init__(self, status: str, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _bad(code: str, message: str) -> ApiError:
    return ApiError("400 Bad Request", code, message)


# ---------------------------------------------------------------- validation

def _string(body, key, *, max_len, required=True):
    v = body.get(key)
    if v is None:
        if required:
            raise _bad("missing_field", f"champ « {key} » obligatoire")
        return None
    if not isinstance(v, str):
        raise _bad("invalid_field", f"« {key} » doit être une chaîne de caractères")
    v = v.strip()
    if not v or len(v) > max_len or _CONTROL_RE.search(v):
        raise _bad("invalid_field", f"« {key} » est vide, trop long ou contient des caractères interdits")
    return v


def _number(body, key, lo, hi):
    v = body.get(key)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
        raise _bad("invalid_field", f"« {key} » doit être un nombre entre {lo} et {hi}")
    return float(v)


def parse_request(body) -> dict:
    """Valide l'entrée. Lève ApiError (400 ou 422) au moindre écart."""
    if not isinstance(body, dict):
        raise _bad("invalid_json", "le corps doit être un objet JSON")
    unknown = set(body) - FIELDS
    if unknown:
        raise _bad("unknown_field", f"champ(s) inconnu(s) : {', '.join(sorted(unknown))}")

    precision = body.get("time_precision")
    if precision not in PRECISIONS:
        raise _bad("invalid_field", "« time_precision » doit valoir exacte, approximative ou inconnue")
    if precision == "inconnue":
        # Aucun calcul : sans heure, le type et l'autorité peuvent être faux.
        raise ApiError("422 Unprocessable Entity", "time_unknown",
                       "Heure de naissance inconnue : le thème n'est pas calculé, car sans heure "
                       "le type et l'autorité peuvent être faux.")

    d = _string(body, "date", max_len=10)
    if not _DATE_RE.fullmatch(d):
        raise _bad("invalid_field", "« date » doit être au format AAAA-MM-JJ")
    try:
        day = Date.fromisoformat(d)
    except ValueError:
        raise _bad("invalid_field", "« date » n'existe pas dans le calendrier") from None
    if not MIN_YEAR <= day.year <= MAX_YEAR:
        raise _bad("invalid_field", f"« date » doit être entre {MIN_YEAR} et {MAX_YEAR}")

    t = _string(body, "time", max_len=5)
    if not _TIME_RE.fullmatch(t):
        raise _bad("invalid_field", "« time » doit être au format HH:MM")
    hh, mm = int(t[:2]), int(t[3:])
    if hh > 23 or mm > 59:
        raise _bad("invalid_field", "« time » n'est pas une heure valide")

    has_tz = body.get("tz") is not None
    has_coords = body.get("lat") is not None or body.get("lon") is not None
    has_place = body.get("place") is not None
    if has_tz + has_coords + has_place != 1:
        raise _bad("invalid_location", "fournir exactement un lieu : « tz », ou « lat » + « lon », ou « place »")
    loc = {}
    if has_tz:
        tz = _string(body, "tz", max_len=64)
        if tz not in _TIMEZONES:
            raise _bad("invalid_field", "« tz » n'est pas un fuseau IANA connu (ex. Europe/Paris)")
        loc["tz"] = tz
    elif has_coords:
        loc["lat"] = _number(body, "lat", -90, 90)
        loc["lon"] = _number(body, "lon", -180, 180)
    else:
        loc["place"] = _string(body, "place", max_len=MAX_PLACE)

    name = _string(body, "name", max_len=MAX_NAME, required=False) or ""

    skin = body.get("skin", "atlas")
    if skin not in SKINS:
        raise _bad("invalid_field", f"« skin » doit valoir {' ou '.join(SKINS)}")
    if "theme" in body:  # thème de marque : atlas (Human Atlas) ou gdh (GoDesignHumain)
        if body["theme"] not in PUBLIC_THEMES:
            raise ApiError("422 Unprocessable Entity", "invalid_theme",
                           f"« theme » doit valoir {' ou '.join(PUBLIC_THEMES)}")
        if "skin" in body:
            raise ApiError("422 Unprocessable Entity", "invalid_theme",
                           "« theme » et « skin » ne se combinent pas : n'en donner qu'un")
        skin = body["theme"]

    include_svg = body.get("include_svg", True)
    if not isinstance(include_svg, bool):
        raise _bad("invalid_field", "« include_svg » doit valoir true ou false")

    want_details = body.get("details", False)
    if not isinstance(want_details, bool):
        raise _bad("invalid_field", "« details » doit valoir true ou false")
    want_keys = body.get("content_keys", False)
    if not isinstance(want_keys, bool):
        raise _bad("invalid_field", "« content_keys » doit valoir true ou false")

    return {"local": datetime(day.year, day.month, day.day, hh, mm), "precision": precision,
            **loc, "name": name, "skin": skin, "include_svg": include_svg, "details": want_details,
            "content_keys": want_keys}


# ---------------------------------------------------------------- calcul

def resolve_place(req: dict) -> dict:
    """Fuseau horaire et lieu retenu, à renvoyer pour que l'app puisse le montrer."""
    if "tz" in req:
        return {"tz": req["tz"]}
    if "lat" in req:
        try:
            tz = timezone_at(req["lat"], req["lon"])
        except ValueError:
            raise ApiError("422 Unprocessable Entity", "place_not_found",
                           "Aucun fuseau horaire pour ces coordonnées.") from None
        return {"lat": req["lat"], "lon": req["lon"], "tz": tz}
    try:
        p = geocode(req["place"])
    except GeocodingUnavailable:
        raise ApiError("503 Service Unavailable", "geocoding_unavailable",
                       "Le service de géocodage ne répond pas. Réessayer, ou envoyer « tz » ou « lat » + « lon ».") from None
    except ValueError:
        raise ApiError("422 Unprocessable Entity", "place_not_found",
                       "Lieu introuvable. Préciser la ville et le pays, ou envoyer « lat » + « lon ».") from None
    out = {"name": p.name, "lat": p.lat, "lon": p.lon, "tz": p.tz}
    if p.alternatives:
        out["ambiguous"] = True
        out["alternatives"] = p.alternatives
    return out


def _activation(a) -> dict:
    return {"gate": a.gate, "line": a.line, "color": a.color, "tone": a.tone, "base": a.base,
            "fixing": a.fixing, "label": a.label, "longitude": round(a.longitude, 6)}


def details(c) -> dict:
    """Le thème complet : chaque planète côté Personnalité et Design, variables, quart.
    (Pas de données de naissance en clair : seulement les instants UTC calculés.)"""
    return {
        "birth_utc": c.birth_utc.isoformat(),
        "design_utc": c.design_utc.isoformat(),
        "cross_gates": c.cross_gates,
        "quarter": c.meta["quarter"],
        "variables": c.variables,
        "personality": {p: _activation(c.personality[p]) for p in D.PLANETS},
        "design": {p: _activation(c.design[p]) for p in D.PLANETS},
    }


def chart_for(req: dict):
    """Thème d'une personne validée par parse_request : (thème, lieu retenu, avertissement)."""
    place = resolve_place(req)
    rt = local_to_utc(req["local"], place["tz"])
    warnings = []
    if rt.warning:
        warnings.append(rt.warning)
    if req["precision"] == "approximative":
        warnings.append("Heure approximative : le profil, la croix ou certaines portes peuvent changer.")
    if place.get("ambiguous"):
        warnings.append("Plusieurs lieux portent ce nom : vérifier le lieu retenu.")
    return build_chart(rt.utc, req["name"]), place, " ".join(warnings) or None


def compute(req: dict) -> dict:
    c, place, warning = chart_for(req)
    out = {
        "type": c.type,
        "type_fr": D.TYPES_FR[c.type][0],
        "authority": c.authority,
        "authority_fr": D.AUTHORITY_FR[c.authority],
        "profile": c.profile,
        "profile_label": _profile_label(c.profile),
        "cross": c.cross,
        "channels": [f"{a}-{b}" for a, b in c.channels],
        "defined_centers": c.defined_centers,
        "definition": c.definition,
        "active_gates": {str(g): sides for g, sides in c.active_gates.items()},
        "summary": summary_sentence(c),
        "place_resolved": place,
        "time_warning": warning,
        "details": details(c),
    }
    if req["include_svg"]:
        out["svg"] = render_bodygraph(c, skin=req["skin"], name=req["name"])
    if req.get("details"):  # option : la réponse sans elle reste identique
        out.update(premium_details(c, req["precision"]))
    if req.get("content_keys"):  # option : clés des textes d'interprétation (textes hors dépôt)
        out["content_keys"] = chart_keys(c)
    return out


def premium_details(c, time_precision: str) -> dict:
    """Couleur, ton, base et sensibilité à l'heure de chaque activation ; variables ; précision."""
    stab = P.stable_minutes(c)
    acts = {side: {p: {**_activation(getattr(c, side)[p]), "stable_minutes": stab[side][p]}
                   for p in D.PLANETS}
            for side in ("personality", "design")}
    return {"activations_details": acts, "variables": P.variables(c),
            "precision": P.precision(c, time_precision, stab)}


COMPOSITE_FIELDS = {"people", "include_svg"}


def parse_composite(body) -> dict:
    """Deux personnes, chacune au format de /v1/chart (sans « include_svg », « skin », « details »)."""
    if not isinstance(body, dict):
        raise _bad("invalid_json", "le corps doit être un objet JSON")
    unknown = set(body) - COMPOSITE_FIELDS
    if unknown:
        raise _bad("unknown_field", f"champ(s) inconnu(s) : {', '.join(sorted(unknown))}")
    people = body.get("people")
    if not isinstance(people, list) or len(people) != 2:
        raise _bad("invalid_field", "« people » doit contenir exactement 2 personnes")
    parsed = []
    for i, person in enumerate(people, 1):
        if isinstance(person, dict) and set(person) & {"include_svg", "skin", "theme", "details", "content_keys"}:
            raise _bad("unknown_field", f"personne {i} : « include_svg », « skin » et « details » se règlent pour toute la composite")
        try:
            parsed.append(parse_request(person))
        except ApiError as e:
            raise ApiError(e.status, e.code, f"personne {i} : {e.message}") from None
    include_svg = body.get("include_svg", True)
    if not isinstance(include_svg, bool):
        raise _bad("invalid_field", "« include_svg » doit valoir true ou false")
    return {"people": parsed, "include_svg": include_svg}


GROUP_FIELDS = {"people"}


def parse_group(body) -> dict:
    """De 3 à 5 personnes, chacune au format de /v1/chart (sans « include_svg », « skin », « details »)."""
    if not isinstance(body, dict):
        raise _bad("invalid_json", "le corps doit être un objet JSON")
    unknown = set(body) - GROUP_FIELDS
    if unknown:
        raise _bad("unknown_field", f"champ(s) inconnu(s) : {', '.join(sorted(unknown))}")
    people = body.get("people")
    if not isinstance(people, list) or not MIN_PEOPLE <= len(people) <= MAX_PEOPLE:
        raise _bad("invalid_field", f"« people » doit contenir de {MIN_PEOPLE} à {MAX_PEOPLE} personnes")
    return {"people": [_parse_person(person, i) for i, person in enumerate(people, 1)]}


def compute_group(req: dict) -> dict:
    results = [chart_for(p) for p in req["people"]]
    return {
        "people": [_person_summary(p, c, place, warning) for p, (c, place, warning) in zip(req["people"], results)],
        "group": group([c for c, _, _ in results]),
    }


def _parse_person(person, i: int) -> dict:
    if isinstance(person, dict) and set(person) & {"include_svg", "skin", "theme", "details", "content_keys"}:
        raise _bad("unknown_field", f"personne {i} : « include_svg », « skin » et « details » ne s'appliquent pas ici")
    try:
        return parse_request(person)
    except ApiError as e:
        raise ApiError(e.status, e.code, f"personne {i} : {e.message}") from None


def _person_summary(p, c, place, warning) -> dict:
    return {"name": p["name"] or None, "type": c.type, "type_fr": D.TYPES_FR[c.type][0],
            "authority": c.authority, "profile": c.profile,
            "channels": [f"{a}-{b}" for a, b in c.channels], "defined_centers": c.defined_centers,
            "place_resolved": place, "time_warning": warning}


def compute_composite(req: dict) -> dict:
    results = [chart_for(p) for p in req["people"]]
    (ca, _, _), (cb, _, _) = results
    out = {
        "people": [_person_summary(p, c, place, warning) for p, (c, place, warning) in zip(req["people"], results)],
        "composite": composite(ca, cb),
    }
    if req["include_svg"]:
        out["svg"] = render_composite(ca, cb, req["people"][0]["name"], req["people"][1]["name"])
    return out


TRANSIT_FIELDS = {"at", "chart"}


def _instant(value) -> datetime:
    """Instant ISO 8601 avec fuseau (« 2026-10-28T14:00:00Z » ou « …+01:00 »)."""
    if not isinstance(value, str) or len(value) > 40:
        raise _bad("invalid_field", "« at » doit être une date-heure ISO 8601 avec fuseau, ex. 2026-10-28T14:00:00Z")
    try:
        when = datetime.fromisoformat(value.strip())
    except ValueError:
        raise _bad("invalid_field", "« at » doit être une date-heure ISO 8601 avec fuseau, ex. 2026-10-28T14:00:00Z") from None
    if when.tzinfo is None:
        raise _bad("invalid_field", "« at » doit préciser son fuseau (Z ou +01:00)")
    if not MIN_YEAR <= when.year <= MAX_YEAR:
        raise _bad("invalid_field", f"« at » doit être entre {MIN_YEAR} et {MAX_YEAR}")
    return when.astimezone(timezone.utc)


def parse_transit(body) -> dict:
    if not isinstance(body, dict):
        raise _bad("invalid_json", "le corps doit être un objet JSON")
    unknown = set(body) - TRANSIT_FIELDS
    if unknown:
        raise _bad("unknown_field", f"champ(s) inconnu(s) : {', '.join(sorted(unknown))}")
    when = _instant(body["at"]) if body.get("at") is not None else datetime.now(timezone.utc)
    person = body.get("chart")
    if person is not None and isinstance(person, dict) and set(person) & {"include_svg", "skin", "theme", "details", "content_keys"}:
        raise _bad("unknown_field", "« chart » : « include_svg », « skin » et « details » ne s'appliquent pas ici")
    try:
        natal = parse_request(person) if person is not None else None
    except ApiError as e:
        raise ApiError(e.status, e.code, f"thème natal : {e.message}") from None
    return {"at": when, "chart": natal}


def compute_transit(req: dict) -> dict:
    natal = None
    out_natal = None
    if req["chart"] is not None:
        natal, place, warning = chart_for(req["chart"])
        out_natal = {"type": natal.type, "profile": natal.profile, "defined_centers": natal.defined_centers,
                     "channels": [f"{a}-{b}" for a, b in natal.channels],
                     "place_resolved": place, "time_warning": warning}
    out = transit(req["at"], natal)
    if out_natal is not None:
        out["natal"] = out_natal
    return out


RETURN_FIELDS = {"chart", "kind", "year"}
RETURNS_FR = {"solar": "retour solaire", "saturn": "retour de Saturne", "chiron": "retour de Chiron",
              "uranus_opposition": "opposition d'Uranus"}


def parse_return(body) -> dict:
    if not isinstance(body, dict):
        raise _bad("invalid_json", "le corps doit être un objet JSON")
    unknown = set(body) - RETURN_FIELDS
    if unknown:
        raise _bad("unknown_field", f"champ(s) inconnu(s) : {', '.join(sorted(unknown))}")
    kind = body.get("kind")
    if kind not in RETURNS:
        raise _bad("invalid_field", f"« kind » doit valoir {', '.join(RETURNS)}")
    year = body.get("year")
    if isinstance(year, bool) or not isinstance(year, int) or not MIN_YEAR < year <= MAX_YEAR - 2:
        raise _bad("invalid_field", f"« year » doit être une année entre {MIN_YEAR + 1} et {MAX_YEAR - 2}")
    person = body.get("chart")
    if person is None:
        raise _bad("missing_field", "champ « chart » obligatoire (le thème natal)")
    if isinstance(person, dict) and set(person) & {"include_svg", "skin", "theme", "details", "content_keys"}:
        raise _bad("unknown_field", "« chart » : « include_svg », « skin » et « details » ne s'appliquent pas ici")
    try:
        natal = parse_request(person)
    except ApiError as e:
        raise ApiError(e.status, e.code, f"thème natal : {e.message}") from None
    return {"chart": natal, "kind": kind, "year": year}


def chart_payload(c) -> dict:
    """Le thème, dans les mêmes champs que /v1/chart (sans lieu ni SVG)."""
    return {
        "type": c.type, "type_fr": D.TYPES_FR[c.type][0],
        "authority": c.authority, "authority_fr": D.AUTHORITY_FR[c.authority],
        "profile": c.profile, "profile_label": _profile_label(c.profile), "cross": c.cross,
        "channels": [f"{a}-{b}" for a, b in c.channels], "defined_centers": c.defined_centers,
        "definition": c.definition, "active_gates": {str(g): sides for g, sides in c.active_gates.items()},
        "summary": summary_sentence(c), "details": details(c),
    }


def compute_return(req: dict) -> dict:
    natal, place, warning = chart_for(req["chart"])
    if req["year"] <= natal.birth_utc.year:
        raise _bad("invalid_field", "« year » doit être postérieure à l'année de naissance")
    passages = find_returns(natal, req["kind"], req["year"])
    out = {
        "kind": req["kind"], "kind_fr": RETURNS_FR[req["kind"]], "year": req["year"],
        "natal": {"type": natal.type, "profile": natal.profile, "defined_centers": natal.defined_centers,
                  "channels": [f"{a}-{b}" for a, b in natal.channels],
                  "place_resolved": place, "time_warning": warning},
        "passages": [{
            "utc": p.when_utc.replace(microsecond=0).isoformat(),
            "retrograde": p.retrograde, "age_years": p.age_years,
            "chart": chart_payload(p.chart),
            "overlay": overlay(natal, {f"{side}_{k}": a for side in ("personality", "design")
                                      for k, a in getattr(p.chart, side).items()}),
        } for p in passages],
    }
    if not passages and req["kind"] != "solar":
        out["years_with_returns"] = years_with_returns(natal, req["kind"], MAX_YEAR - 1)
    return out


def parse_day(query: str) -> dict:
    q = parse_qs(query or "", max_num_fields=4)
    unknown = set(q) - {"date", "tz"}
    if unknown:
        raise _bad("unknown_field", f"paramètre(s) inconnu(s) : {', '.join(sorted(unknown))}")
    day_s, tz = (q.get("date") or [None])[0], (q.get("tz") or ["Europe/Paris"])[0]
    if not day_s or not _DATE_RE.fullmatch(day_s):
        raise _bad("invalid_field", "« date » doit être au format AAAA-MM-JJ")
    try:
        day = Date.fromisoformat(day_s)
    except ValueError:
        raise _bad("invalid_field", "« date » n'existe pas dans le calendrier") from None
    if not MIN_YEAR <= day.year <= MAX_YEAR:
        raise _bad("invalid_field", f"« date » doit être entre {MIN_YEAR} et {MAX_YEAR}")
    if tz not in _TIMEZONES:
        raise _bad("invalid_field", "« tz » n'est pas un fuseau IANA connu (ex. Europe/Paris)")
    return {"day": day, "tz": tz}


# ---------------------------------------------------------------- WSGI

def _json(start_response, status: str, payload: dict):
    body = json.dumps(payload, ensure_ascii=False).encode()
    start_response(status, [("Content-Type", "application/json; charset=utf-8"),
                            ("Content-Length", str(len(body))),
                            ("Cache-Control", "no-store")])
    return [body]


def _error(start_response, e: ApiError):
    return _json(start_response, e.status, {"error": {"code": e.code, "message": e.message}})


def _authorized(environ, *key_names: str) -> bool:
    """Vrai si l'en-tête porte l'une des clés nommées (ENGINE_API_KEY par défaut).
    Une clé absente ou trop courte n'ouvre jamais rien."""
    header = environ.get("HTTP_AUTHORIZATION", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer":
        token = ""
    ok = False
    for name in key_names or ("ENGINE_API_KEY",):
        key = os.environ.get(name, "")
        if len(key) >= MIN_KEY_LENGTH:  # chaque clé comparée, en temps constant
            ok |= hmac.compare_digest(token.strip().encode(), key.encode())
    return ok


def _read_body(environ) -> bytes:
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        raise _bad("invalid_request", "en-tête Content-Length invalide") from None
    if length > MAX_BODY:
        raise ApiError("413 Content Too Large", "body_too_large", f"corps limité à {MAX_BODY} octets")
    body = environ["wsgi.input"].read(length) if length > 0 else b""
    if len(body) > MAX_BODY:
        raise ApiError("413 Content Too Large", "body_too_large", f"corps limité à {MAX_BODY} octets")
    return body


def application(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/") or "/"

    if path == "/":
        if method not in ("GET", "HEAD"):
            return _error(start_response, ApiError("405 Method Not Allowed", "method_not_allowed", "GET uniquement"))
        start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", "2")])
        return [b"ok"]

    if path == "/source":
        # AGPL v3, article 13 : offrir le code source à ceux qui utilisent le service.
        if method not in ("GET", "HEAD"):
            return _error(start_response, ApiError("405 Method Not Allowed", "method_not_allowed", "GET uniquement"))
        url = os.environ.get("SOURCE_URL", "").strip()
        if not url.startswith("https://"):
            return _error(start_response, ApiError("503 Service Unavailable", "source_not_configured",
                                                   "adresse du code source non configurée (SOURCE_URL)"))
        body = url.encode()
        start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8"),
                                  ("Content-Length", str(len(body)))])
        return [body]

    if path == "/v1/transits/day":
        if method not in ("GET", "HEAD"):
            return _error(start_response, ApiError("405 Method Not Allowed", "method_not_allowed", "GET uniquement"))
        # Pas de donnée personnelle : une clé dédiée suffit (option : à donner à d'autres sites).
        if not _authorized(environ, "ENGINE_API_KEY", "TRANSITS_API_KEY"):
            return _error(start_response, ApiError("401 Unauthorized", "unauthorized", "clé d'API absente ou invalide"))
        try:
            req = parse_day(environ.get("QUERY_STRING", ""))
            return _json(start_response, "200 OK", day_changes(req["day"], req["tz"]))
        except ApiError as e:
            return _error(start_response, e)
        except Exception as e:
            log.error("erreur interne : %s", e.__class__.__name__)
            return _error(start_response, ApiError("500 Internal Server Error", "internal_error", "erreur interne du moteur"))

    if path == "/v1/dream":
        # Lot 6 : thème de rêve (Dream Rave). Route réservée : aucun calcul tant que la règle
        # (activations et centres retenus pendant le sommeil) n'a pas été fournie.
        if method != "POST":
            return _error(start_response, ApiError("405 Method Not Allowed", "method_not_allowed", "POST uniquement"))
        if not _authorized(environ):
            return _error(start_response, ApiError("401 Unauthorized", "unauthorized", "clé d'API absente ou invalide"))
        return _error(start_response, ApiError("501 Not Implemented", "pending_specification",
                                               "Thème de rêve (Dream Rave) : en attente de spécification."))

    routes = {"/v1/chart": (parse_request, compute), "/v1/composite": (parse_composite, compute_composite),
              "/v1/transit": (parse_transit, compute_transit), "/v1/return": (parse_return, compute_return),
              "/v1/group": (parse_group, compute_group)}
    if path not in routes:
        return _error(start_response, ApiError("404 Not Found", "not_found", "adresse inconnue"))
    parse, run = routes[path]
    if method != "POST":
        return _error(start_response, ApiError("405 Method Not Allowed", "method_not_allowed", "POST uniquement"))
    if not _authorized(environ):
        return _error(start_response, ApiError("401 Unauthorized", "unauthorized", "clé d'API absente ou invalide"))

    try:
        raw = _read_body(environ)
        try:
            body = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise _bad("invalid_json", "le corps n'est pas un JSON valide") from None
        return _json(start_response, "200 OK", run(parse(body)))
    except ApiError as e:
        return _error(start_response, e)
    except Exception as e:
        # Seulement le type d'erreur : jamais les données de naissance.
        log.error("erreur interne : %s", e.__class__.__name__)
        return _error(start_response, ApiError("500 Internal Server Error", "internal_error", "erreur interne du moteur"))
