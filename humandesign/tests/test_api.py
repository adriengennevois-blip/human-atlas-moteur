# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Teste l'API sans réseau : le géocodage est simulé."""
import io
import json
import logging
from xml.etree import ElementTree

import pytest

import api_app as A
from hd.timeutil import GeocodingUnavailable, Place

KEY = "k" * 40
REFERENCE_1 = {"date": "1999-09-20", "time": "08:26", "time_precision": "exacte", "tz": "Europe/Paris"}


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", KEY)


def call(body=None, *, method="POST", path="/v1/chart", key=KEY, raw=None, headers=None):
    data = raw if raw is not None else json.dumps(body).encode()
    env = {"REQUEST_METHOD": method, "PATH_INFO": path, "CONTENT_LENGTH": str(len(data)),
           "wsgi.input": io.BytesIO(data), **(headers or {})}
    if key is not None:
        env["HTTP_AUTHORIZATION"] = f"Bearer {key}"
    out = {}
    resp = b"".join(A.application(env, lambda s, h: out.update(status=s, headers=dict(h))))
    code = int(out["status"].split()[0])
    try:
        return code, json.loads(resp)
    except json.JSONDecodeError:
        return code, resp.decode()


# ---------------------------------------------------------------- santé

def test_health():
    assert call(method="GET", path="/", key=None) == (200, "ok")


def test_source_returns_public_repository(monkeypatch):
    """AGPL : le service indique où trouver son code source, sans clé d'API."""
    monkeypatch.setenv("SOURCE_URL", "https://github.com/exemple/human-atlas-moteur")
    assert call(method="GET", path="/source", key=None) == (200, "https://github.com/exemple/human-atlas-moteur")
    assert call(method="POST", path="/source", key=None)[0] == 405


@pytest.mark.parametrize("value", [None, "", "pas-une-adresse", "http://non-chiffre.example"])
def test_source_not_configured_is_503(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("SOURCE_URL", raising=False)
    else:
        monkeypatch.setenv("SOURCE_URL", value)
    code, r = call(method="GET", path="/source", key=None)
    assert code == 503 and r["error"]["code"] == "source_not_configured"


def test_unknown_path_and_method():
    assert call(method="GET", path="/v2/x")[0] == 404
    assert call(method="GET")[0] == 405


# ---------------------------------------------------------------- authentification

@pytest.mark.parametrize("key", [None, "", "mauvaise-cle", KEY + "x", KEY[:-1]])
def test_wrong_or_missing_key_is_401(key):
    code, body = call(REFERENCE_1, key=key)
    assert code == 401 and body["error"]["code"] == "unauthorized"


def test_key_must_use_bearer_scheme():
    code, _ = call(REFERENCE_1, key=None, headers={"HTTP_AUTHORIZATION": f"Basic {KEY}"})
    assert code == 401


@pytest.mark.parametrize("server_key", [None, "trop-courte"])
def test_everything_refused_if_server_key_missing_or_short(monkeypatch, server_key):
    if server_key is None:
        monkeypatch.delenv("ENGINE_API_KEY")
    else:
        monkeypatch.setenv("ENGINE_API_KEY", server_key)
    assert call(REFERENCE_1, key=server_key or "")[0] == 401


def test_key_is_compared_in_constant_time(monkeypatch):
    seen = []
    real = A.hmac.compare_digest
    monkeypatch.setattr(A.hmac, "compare_digest", lambda a, b: seen.append(1) or real(a, b))
    call(REFERENCE_1, key="faux")
    assert seen


# ---------------------------------------------------------------- réponse

def test_full_response_for_reference_1():
    code, r = call({**REFERENCE_1, "name": "Référence 1"})
    assert code == 200
    assert set(r) == {"type", "type_fr", "authority", "authority_fr", "profile", "profile_label",
                      "cross", "channels", "defined_centers", "definition", "active_gates",
                      "summary", "place_resolved", "time_warning", "details", "svg"}
    assert (r["type"], r["type_fr"]) == ("Generator", "Générateur")
    assert (r["authority"], r["authority_fr"]) == ("Sacral", "Sacrale")
    assert r["profile"] == "5/1" and r["profile_label"] == "5/1 (Hérétique / Investigateur)"
    assert r["cross"] == "Left Angle Cross of the Plane 2"
    assert r["channels"] == ["3-60", "13-33", "24-61"]
    assert r["defined_centers"] == ["head", "ajna", "throat", "g", "sacral", "root"]
    assert r["definition"] == 3
    assert r["active_gates"]["6"] == ["design", "personality"] and r["active_gates"]["24"] == ["design"]
    assert r["summary"] == "Générateur à autorité sacrale, profil 5/1 (Hérétique / Investigateur)"
    assert r["place_resolved"] == {"tz": "Europe/Paris"}
    assert r["time_warning"] is None
    ElementTree.fromstring(r["svg"])
    assert "Référence 1" in r["svg"]


def test_details_match_reference_1():
    """Le thème complet (13 planètes × 2 côtés) est celui de mybodygraph pour la référence 1."""
    from .test_reference import PLANET_ORDER, REFERENCE_1 as REF
    code, r = call({**REFERENCE_1, "include_svg": False})
    d = r["details"]
    assert " ".join(d["personality"][p]["label"] for p in PLANET_ORDER) == REF["personality"]
    assert " ".join(d["design"][p]["label"] for p in PLANET_ORDER) == REF["design"]
    assert d["cross_gates"] == "6/36 | 15/10" and d["quarter"] in ("Initiation", "Civilisation", "Dualité", "Mutation")
    v = d["variables"]
    assert (v["design_sun"], v["design_node"], v["personality_sun"], v["personality_node"]) == REF["variables"]
    a = d["personality"]["sun"]
    assert set(a) == {"gate", "line", "color", "tone", "base", "fixing", "label", "longitude"}
    assert 1 <= a["color"] <= 6 and 1 <= a["tone"] <= 6 and 1 <= a["base"] <= 5
    assert d["birth_utc"].startswith("1999-09-20T06:26")


def test_without_svg_and_classic_skin():
    code, r = call({**REFERENCE_1, "include_svg": False})
    assert code == 200 and "svg" not in r
    code, r = call({**REFERENCE_1, "skin": "classique"})
    assert code == 200 and "#c62828" in r["svg"]


def test_lat_lon():
    code, r = call({"date": "1999-09-20", "time": "08:26", "time_precision": "exacte",
                    "lat": 45.76, "lon": 4.83})
    assert code == 200 and r["type"] == "Generator"
    assert r["place_resolved"] == {"lat": 45.76, "lon": 4.83, "tz": "Europe/Paris"}


def test_place_is_geocoded_and_returned(monkeypatch):
    monkeypatch.setattr(A, "geocode", lambda q: Place("Lyon, Rhône, France", 45.76, 4.83, "Europe/Paris"))
    code, r = call({"date": "1999-09-20", "time": "08:26", "time_precision": "exacte", "place": "Lyon"})
    assert code == 200 and r["place_resolved"]["name"] == "Lyon, Rhône, France"
    assert r["profile"] == "5/1"


def test_ambiguous_place_is_reported(monkeypatch):
    monkeypatch.setattr(A, "geocode", lambda q: Place(
        "Saint-Denis, France", 48.94, 2.36, "Europe/Paris", ["Saint-Denis, La Réunion, France (Indian/Reunion)"]))
    code, r = call({**REFERENCE_1, "tz": None, "place": "Saint-Denis"})
    assert code == 200 and r["place_resolved"]["ambiguous"] is True
    assert "Plusieurs lieux" in r["time_warning"]


def test_place_not_found_and_geocoder_down(monkeypatch):
    def not_found(q):
        raise ValueError("Lieu introuvable")

    def down(q):
        raise GeocodingUnavailable("panne")
    body = {"date": "1999-09-20", "time": "08:26", "time_precision": "exacte", "place": "zzqx"}
    monkeypatch.setattr(A, "geocode", not_found)
    code, r = call(body)
    assert code == 422 and r["error"]["code"] == "place_not_found"
    monkeypatch.setattr(A, "geocode", down)
    code, r = call(body)
    assert code == 503 and r["error"]["code"] == "geocoding_unavailable"


def test_approximate_time_and_dst_warnings():
    code, r = call({**REFERENCE_1, "time_precision": "approximative"})
    assert code == 200 and "approximative" in r["time_warning"]
    code, r = call({**REFERENCE_1, "date": "2021-03-28", "time": "02:30"})
    assert code == 200 and "inexistante" in r["time_warning"]


# ---------------------------------------------------------------- heure inconnue

def test_unknown_time_is_refused_without_computing(monkeypatch):
    monkeypatch.setattr(A, "build_chart", lambda *a, **k: pytest.fail("ne doit pas calculer"))
    monkeypatch.setattr(A, "geocode", lambda q: pytest.fail("ne doit pas géocoder"))
    code, r = call({"date": "1999-09-20", "time_precision": "inconnue", "place": "Lyon"})
    assert code == 422 and r["error"]["code"] == "time_unknown"
    assert "heure" in r["error"]["message"].lower()


# ---------------------------------------------------------------- validation

@pytest.mark.parametrize("patch", [
    {"date": "20/09/1999"}, {"date": "1999-02-30"}, {"date": "1700-01-01"}, {"date": 19990920},
    {"time": "8:26"}, {"time": "24:00"}, {"time": "08:60"}, {"time": "08:26:00"},
    {"time_precision": "exact"}, {"time_precision": None},
    {"tz": "Europe/Lyon"}, {"tz": "../../etc/passwd"},
    {"skin": "rose"}, {"include_svg": "oui"}, {"name": 12}, {"name": "x" * 61}, {"name": "a\x00b"},
    {"name": "a\ud800b"}, {"inconnu": 1},
    {"lat": 45.0, "lon": 4.0},                          # deux lieux à la fois
    {"tz": None},                                       # aucun lieu
    {"tz": None, "lat": 91, "lon": 0}, {"tz": None, "lat": True, "lon": 0},
    {"tz": None, "lat": 45.0},                          # lon manquant
    {"tz": None, "place": ""}, {"tz": None, "place": "x" * 201},
])
def test_invalid_input_is_400(patch):
    body = {k: v for k, v in {**REFERENCE_1, **patch}.items() if v is not None}
    code, r = call(body)
    assert code == 400, (patch, r)
    assert set(r["error"]) == {"code", "message"}


@pytest.mark.parametrize("raw", [b"", b"{", b"[1, 2]", b'"texte"', b"\xff\xfe"])
def test_not_a_json_object_is_400(raw):
    code, r = call(raw=raw)
    assert code == 400 and "error" in r


def test_body_limited_to_10_kb():
    big = json.dumps({**REFERENCE_1, "name": "x" * 11000}).encode()
    assert call(raw=big)[0] == 413
    # Content-Length mensonger : on ne lit jamais plus que la limite
    env_body = {**REFERENCE_1}
    code, _ = call(env_body, headers={"CONTENT_LENGTH": "999999"})
    assert code == 413


# ---------------------------------------------------------------- prénom

@pytest.mark.parametrize("name", ['<script>alert("x")</script>', "Zoé & <Léa>", 'Dit "Doudou"', "O'Neil"])
def test_name_is_escaped_in_svg(name):
    code, r = call({**REFERENCE_1, "name": name})
    assert code == 200
    ElementTree.fromstring(r["svg"])
    assert "<script>" not in r["svg"]


# ---------------------------------------------------------------- données personnelles

def test_no_birth_data_in_logs(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(A, "build_chart", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("1999-09-20 Lyon")))
    code, r = call({**REFERENCE_1, "name": "Référence 1"})
    assert code == 500 and r["error"]["code"] == "internal_error"
    assert "1999" not in r["error"]["message"]
    for rec in caplog.records:
        msg = rec.getMessage()
        assert "1999" not in msg and "Référence" not in msg and "Lyon" not in msg
        assert rec.exc_info is None


def test_responses_are_not_cached():
    env = {"REQUEST_METHOD": "POST", "PATH_INFO": "/v1/chart", "HTTP_AUTHORIZATION": f"Bearer {KEY}",
           "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO(b"")}
    out = {}
    A.application(env, lambda s, h: out.update(dict(h)))
    assert out["Cache-Control"] == "no-store"
