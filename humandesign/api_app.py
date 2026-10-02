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
  POST /v1/chart    → thème calculé (+ SVG du bodygraph)

Application WSGI sans framework : tourne telle quelle sur o2switch
(cPanel → « Setup Python App », via passenger_wsgi.py).

Réglages (variables d'environnement, à saisir dans cPanel) :
  ENGINE_API_KEY   clé partagée avec l'app (au moins 32 caractères)
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
from datetime import date as Date, datetime
from zoneinfo import available_timezones

from hd import data as D
from hd.bodygraph import SKINS, render_bodygraph, summary_sentence, validate_template
from hd.chart import build_chart
from hd.signup import _profile_label
from hd.timeutil import GeocodingUnavailable, geocode, local_to_utc, timezone_at

log = logging.getLogger("hd-api")

MAX_BODY = 10 * 1024
MIN_KEY_LENGTH = 32
# Les fichiers d'éphémérides couvrent 1800-2400 ; le Design remonte ~88 jours avant.
MIN_YEAR, MAX_YEAR = 1801, 2399
PRECISIONS = ("exacte", "approximative", "inconnue")
FIELDS = {"date", "time", "time_precision", "tz", "lat", "lon", "place", "name", "skin", "include_svg"}
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

    include_svg = body.get("include_svg", True)
    if not isinstance(include_svg, bool):
        raise _bad("invalid_field", "« include_svg » doit valoir true ou false")

    return {"local": datetime(day.year, day.month, day.day, hh, mm), "precision": precision,
            **loc, "name": name, "skin": skin, "include_svg": include_svg}


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


def compute(req: dict) -> dict:
    place = resolve_place(req)
    rt = local_to_utc(req["local"], place["tz"])
    warnings = []
    if rt.warning:
        warnings.append(rt.warning)
    if req["precision"] == "approximative":
        warnings.append("Heure approximative : le profil, la croix ou certaines portes peuvent changer.")
    if place.get("ambiguous"):
        warnings.append("Plusieurs lieux portent ce nom : vérifier le lieu retenu.")

    c = build_chart(rt.utc, req["name"])
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
        "time_warning": " ".join(warnings) or None,
    }
    if req["include_svg"]:
        out["svg"] = render_bodygraph(c, skin=req["skin"], name=req["name"])
    return out


# ---------------------------------------------------------------- WSGI

def _json(start_response, status: str, payload: dict):
    body = json.dumps(payload, ensure_ascii=False).encode()
    start_response(status, [("Content-Type", "application/json; charset=utf-8"),
                            ("Content-Length", str(len(body))),
                            ("Cache-Control", "no-store")])
    return [body]


def _error(start_response, e: ApiError):
    return _json(start_response, e.status, {"error": {"code": e.code, "message": e.message}})


def _authorized(environ) -> bool:
    key = os.environ.get("ENGINE_API_KEY", "")
    if len(key) < MIN_KEY_LENGTH:
        return False  # clé absente ou trop courte : tout refuser
    header = environ.get("HTTP_AUTHORIZATION", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer":
        token = ""
    return hmac.compare_digest(token.strip().encode(), key.encode())


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

    if path != "/v1/chart":
        return _error(start_response, ApiError("404 Not Found", "not_found", "adresse inconnue"))
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
        return _json(start_response, "200 OK", compute(parse_request(body)))
    except ApiError as e:
        return _error(start_response, e)
    except Exception as e:
        # Seulement le type d'erreur : jamais les données de naissance.
        log.error("erreur interne : %s", e.__class__.__name__)
        return _error(start_response, ApiError("500 Internal Server Error", "internal_error", "erreur interne du moteur"))
