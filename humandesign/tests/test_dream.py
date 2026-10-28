# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Lot 6 : thème de rêve, route réservée en attendant sa règle."""
import pytest

from .test_api import KEY, call


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", KEY)


def test_dream_is_pending_specification():
    code, r = call({"date": "1900-01-01", "time": "00:00", "time_precision": "exacte", "tz": "Europe/Paris"},
                   path="/v1/dream")
    assert code == 501 and r["error"]["code"] == "pending_specification"


def test_dream_requires_the_key_and_post():
    assert call({}, path="/v1/dream", key=None)[0] == 401
    assert call(None, method="GET", path="/v1/dream", raw=b"")[0] == 405
