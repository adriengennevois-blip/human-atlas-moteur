# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Sécurité : une clé par client (X-API-Key), période de transition, limite de débit, CORS, journaux."""
import io
import json
import logging

import pytest

import api_app as A

ATLAS, GDH, LEGACY = "a" * 40, "g" * 40, "k" * 40
BIRTH = {"date": "1977-03-14", "time": "03:41", "time_precision": "exacte", "tz": "Europe/Paris", "name": "Sentinelle"}
ALL_POST_ROUTES = ["/v1/chart", "/v1/composite", "/v1/group", "/v1/transit", "/v1/return", "/v1/transit/chart",
                   "/v1/ingresses", "/v1/upcoming", "/v1/dream"]


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    for name in list(__import__("os").environ):
        if name.startswith("API_KEY_") or name in ("ENGINE_API_KEY", "TRANSITS_API_KEY", "REQUIRE_API_KEY",
                                                  "RATE_LIMIT_PER_MINUTE"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("API_KEY_ATLAS", ATLAS)
    monkeypatch.setenv("API_KEY_GDH", GDH)
    A._reset_rate_limits()
    yield
    A._reset_rate_limits()


def req(path="/v1/dream", body=None, *, xkey=None, bearer=None, headers=None, method="POST"):
    data = json.dumps(body if body is not None else {}).encode()
    env = {"REQUEST_METHOD": method, "PATH_INFO": path, "CONTENT_LENGTH": str(len(data)),
           "wsgi.input": io.BytesIO(data), **(headers or {})}
    if xkey is not None:
        env["HTTP_X_API_KEY"] = xkey
    if bearer is not None:
        env["HTTP_AUTHORIZATION"] = f"Bearer {bearer}"
    out = {}
    raw = b"".join(A.application(env, lambda s, h: out.update(status=s, headers=dict(h))))
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = raw.decode()
    return int(out["status"].split()[0]), out["headers"], payload


# ---------------------------------------------------------------- une clé par client

def test_each_client_has_its_own_key():
    assert req(xkey=ATLAS)[0] == 501 and req(xkey=GDH)[0] == 501   # 501 : la route « dream » est réservée, clé acceptée
    assert req(xkey="x" * 40)[0] == 401 and req(xkey=ATLAS[:-1])[0] == 401 and req(xkey=ATLAS + "x")[0] == 401


def test_a_client_key_also_works_as_a_bearer_token():
    assert req(bearer=GDH)[0] == 501


def test_a_short_client_key_opens_nothing(monkeypatch):
    monkeypatch.setenv("API_KEY_TEST", "court")
    assert req(xkey="court")[0] == 401 and req(xkey="")[0] == 401


@pytest.mark.parametrize("require", [None, "true", "false"])
@pytest.mark.parametrize("path", ALL_POST_ROUTES)
def test_no_key_is_always_401(monkeypatch, path, require):
    if require is not None:
        monkeypatch.setenv("REQUIRE_API_KEY", require)
    code, _, body = req(path, {})
    assert code == 401 and body["error"]["code"] == "unauthorized"


@pytest.mark.parametrize("require", [None, "true"])
def test_day_view_needs_a_key_too(monkeypatch, require):
    if require:
        monkeypatch.setenv("REQUIRE_API_KEY", require)
    h = {"QUERY_STRING": "date=2026-11-02&tz=Europe/Paris"}
    assert req("/v1/transits/day", method="GET", headers=h)[0] == 401
    assert req("/v1/transits/day", method="GET", headers=h, xkey=GDH)[0] == 200


def test_health_and_source_stay_public(monkeypatch):
    monkeypatch.setenv("SOURCE_URL", "https://github.com/exemple/human-atlas-moteur")
    assert req("/", method="GET")[0] == 200 and req("/source", method="GET")[0] == 200


# ---------------------------------------------------------------- transition : Human Atlas ne change pas

def test_atlas_old_bearer_key_keeps_working_during_the_transition(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", LEGACY)
    assert req(bearer=LEGACY)[0] == 501                         # l'appel actuel d'Atlas
    assert req(xkey=LEGACY)[0] == 501                           # ou la même clé dans X-API-Key
    code, _, body = req(bearer="mauvaise" * 6)
    assert code == 401


def test_require_api_key_true_ends_the_transition(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", LEGACY)
    monkeypatch.setenv("REQUIRE_API_KEY", "true")
    assert req(bearer=LEGACY)[0] == 401 and req(xkey=LEGACY)[0] == 401   # l'ancienne clé ne passe plus
    assert req(xkey=ATLAS)[0] == 501 and req(xkey=GDH)[0] == 501         # les clés par client, oui
    monkeypatch.setenv("REQUIRE_API_KEY", "TRUE")
    assert req(bearer=LEGACY)[0] == 401
    monkeypatch.setenv("REQUIRE_API_KEY", "false")
    assert req(bearer=LEGACY)[0] == 501


def test_transits_key_stays_limited_to_the_day_view(monkeypatch):
    monkeypatch.setenv("TRANSITS_API_KEY", "t" * 40)
    h = {"QUERY_STRING": "date=2026-11-02&tz=Europe/Paris"}
    assert req("/v1/transits/day", method="GET", headers=h, bearer="t" * 40)[0] == 200
    assert req("/v1/dream", bearer="t" * 40)[0] == 401


def test_key_is_compared_in_constant_time(monkeypatch):
    seen = []
    real = A.hmac.compare_digest
    monkeypatch.setattr(A.hmac, "compare_digest", lambda a, b: seen.append(1) or real(a, b))
    req(xkey="faux")
    assert len(seen) >= 2   # chaque clé de client est comparée, sans s'arrêter à la première


def test_keys_are_never_in_the_responses_or_logs(caplog):
    caplog.set_level(logging.DEBUG)
    code, headers, body = req(xkey=GDH)
    assert ATLAS not in json.dumps(body) and GDH not in json.dumps(body) and GDH not in json.dumps(headers)
    assert all(GDH not in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------- limite de débit

def test_rate_limit_per_key_returns_429(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
    assert [req(xkey=GDH)[0] for _ in range(3)] == [501, 501, 501]
    code, headers, body = req(xkey=GDH)
    assert code == 429 and body["error"]["code"] == "rate_limited"
    assert 1 <= int(headers["Retry-After"]) <= 60
    assert req(xkey=ATLAS)[0] == 501                         # l'autre client n'est pas touché
    assert req(xkey=GDH)[0] == 429                           # et GDH reste bloqué


def test_rate_limit_window_slides(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    clock = [1000.0]
    monkeypatch.setattr(A, "_now", lambda: clock[0])
    assert req(xkey=GDH)[0] == 501
    clock[0] += 30
    assert req(xkey=GDH)[0] == 501
    clock[0] += 10
    code, headers, _ = req(xkey=GDH)
    assert code == 429 and int(headers["Retry-After"]) == 20     # la 1re requête sort de la fenêtre dans 20 s
    clock[0] += 21
    assert req(xkey=GDH)[0] == 501
    assert req(xkey=GDH)[0] == 429


def test_rate_limit_default_off_switch_and_bad_value(monkeypatch):
    assert A.DEFAULT_RATE_LIMIT == 120
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")
    assert all(req(xkey=GDH)[0] == 501 for _ in range(5))
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "beaucoup")
    A._reset_rate_limits()
    assert all(req(xkey=GDH)[0] == 501 for _ in range(5))     # valeur illisible : défaut de 120


def test_default_limit_is_120_per_minute():
    for _ in range(120):
        assert req(xkey=GDH)[0] == 501
    assert req(xkey=GDH)[0] == 429


def test_failed_calls_do_not_use_up_a_clients_allowance(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    for _ in range(5):
        assert req(xkey="x" * 40)[0] == 401
    assert req(xkey=GDH)[0] == 501 and req(xkey=GDH)[0] == 501


def test_the_old_key_is_not_rate_limited_during_the_transition(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", LEGACY)
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    assert all(req(bearer=LEGACY)[0] == 501 for _ in range(6))   # Human Atlas : rien ne change


# ---------------------------------------------------------------- CORS : jamais d'appel direct d'un navigateur

@pytest.mark.parametrize("path", ALL_POST_ROUTES)
def test_calls_from_a_browser_are_refused_even_with_a_valid_key(path):
    code, headers, body = req(path, {}, xkey=GDH, headers={"HTTP_ORIGIN": "https://godesignhumain.fr"})
    assert code == 403 and body["error"]["code"] == "browser_not_allowed"
    assert not [h for h in headers if h.lower().startswith("access-control")]


def test_preflight_gets_no_cors_headers():
    for env in ({"HTTP_ORIGIN": "https://godesignhumain.fr", "HTTP_ACCESS_CONTROL_REQUEST_METHOD": "POST"},
                {"HTTP_ACCESS_CONTROL_REQUEST_METHOD": "POST"}):
        code, headers, _ = req("/v1/chart", {}, method="OPTIONS", headers=env)
        assert code in (403, 405)
        assert not [h for h in headers if h.lower().startswith("access-control")]


def test_no_response_ever_carries_cors_headers(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    for kw in ({"xkey": GDH}, {"xkey": "x" * 40}, {"xkey": GDH}, {}):
        code, headers, _ = req(**kw)
        assert not [h for h in headers if h.lower().startswith("access-control")], code
    assert req("/", method="GET")[1].get("Access-Control-Allow-Origin") is None


def test_servers_without_an_origin_header_are_not_affected():
    assert req(xkey=GDH)[0] == 501


# ---------------------------------------------------------------- aucune donnée de naissance dans les journaux

def _logged(caplog):
    return " ".join(r.getMessage() for r in caplog.records) + " ".join(str(r.exc_info) for r in caplog.records)


@pytest.mark.parametrize("path,extra", [
    ("/v1/chart", {}), ("/v1/transit/chart", {"at": "2026-11-02T12:00:00Z"}),
    ("/v1/upcoming", {"at": "2026-11-02T12:00:00Z"}),
])
def test_no_birth_data_in_logs_on_the_new_routes(caplog, path, extra):
    caplog.set_level(logging.DEBUG)
    body = {**BIRTH, **extra} if path == "/v1/chart" else {"chart": BIRTH, **extra}
    assert req(path, body, xkey=GDH)[0] == 200
    text = _logged(caplog)
    for secret in ("1977", "03:41", "Sentinelle", "Europe/Paris"):
        assert secret not in text, secret


def test_no_birth_data_in_logs_on_failures(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    boom = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("1977-03-14 03:41 Sentinelle Lyon"))
    monkeypatch.setattr(A, "transit_on_chart", boom)
    monkeypatch.setattr(A, "upcoming", boom)
    monkeypatch.setattr(A, "person_intervals", boom)
    cases = [("/v1/transit/chart", {"chart": BIRTH}), ("/v1/upcoming", {"chart": BIRTH}),
             ("/v1/ingresses", {"from": "2026-11-02T00:00:00Z", "to": "2026-11-09T00:00:00Z", "chart": BIRTH})]
    for path, body in cases:
        code, _, payload = req(path, body, xkey=GDH)
        assert code == 500 and payload["error"]["code"] == "internal_error"
        assert "1977" not in json.dumps(payload) and "Sentinelle" not in json.dumps(payload)
    # refus (401, 403, 429) et erreurs de saisie : rien non plus
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    A._reset_rate_limits()
    req("/v1/upcoming", {"chart": BIRTH}, xkey=ATLAS)
    req("/v1/upcoming", {"chart": BIRTH}, xkey=ATLAS)                      # 429
    req("/v1/upcoming", {"chart": BIRTH})                                  # 401
    req("/v1/upcoming", {"chart": BIRTH}, xkey=GDH, headers={"HTTP_ORIGIN": "https://x.fr"})   # 403
    req("/v1/upcoming", {"chart": {**BIRTH, "time": "99:99"}}, xkey=GDH)   # 400
    text = _logged(caplog)
    for secret in ("1977", "03:41", "99:99", "Sentinelle", "Lyon"):
        assert secret not in text, secret
    assert all(r.exc_info is None for r in caplog.records)
