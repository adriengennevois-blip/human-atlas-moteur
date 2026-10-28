# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Lot 7 : clés de contenu (les textes, eux, ne sont pas dans ce dépôt)."""
import json
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hd.chart import build_chart
from hd.content_keys import all_keys, chart_keys, cross_key, manifest
from hd.timeutil import local_to_utc

from .test_api import KEY, REFERENCE_1 as API_REF_1, call
from .test_reference import REFERENCE_1

MANIFEST = Path(__file__).parents[1] / "content-keys.json"
KEY_RE = re.compile(r"^[a-z]+(\.[a-z0-9]+(-[a-z0-9]+)*)+$")


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", KEY)


def test_every_category_has_the_expected_number_of_keys():
    assert manifest()["counts"] == {"type": 5, "authority": 8, "profile": 12, "definition": 5, "center": 18,
                                    "gate": 64, "line": 384, "channel": 36, "cross": 192, "variable": 32,
                                    "total": 756}


def test_keys_are_unique_and_well_formed():
    keys = [k for ks in all_keys().values() for k in ks]
    assert len(keys) == len(set(keys))
    assert all(KEY_RE.match(k) for k in keys), [k for k in keys if not KEY_RE.match(k)]


def test_committed_file_is_up_to_date():
    """content-keys.json est régénéré par « python -m hd.content_keys > content-keys.json »."""
    assert json.loads(MANIFEST.read_text(encoding="utf-8")) == manifest()


def test_examples_from_the_brief():
    keys = {k for ks in all_keys().values() for k in ks}
    for k in ("type.generator", "authority.sacral", "profile.5-1", "center.throat.defined", "center.throat.open",
              "gate.24", "gate.24.line.6", "channel.24-61", "cross.left-angle.plane.2",
              "variable.determination.color-3", "definition.triple-split"):
        assert k in keys, k


def test_reference_1_keys():
    c = build_chart(local_to_utc(REFERENCE_1["local"], REFERENCE_1["tz"]).utc)
    k = chart_keys(c)
    assert (k["type"], k["authority"], k["profile"], k["definition"], k["cross"]) == (
        "type.generator", "authority.sacral", "profile.5-1", "definition.triple-split", "cross.left-angle.plane.2")
    assert k["channels"] == ["channel.3-60", "channel.13-33", "channel.24-61"]
    assert "center.throat.defined" in k["centers"] and "center.spleen.open" in k["centers"] and len(k["centers"]) == 9
    assert k["variables"][:2] == ["variable.determination.right", "variable.determination.color-4"]


def test_every_chart_only_uses_listed_keys():
    """600 thèmes tirés au hasard (1801-2399) : chacune de leurs clés existe dans la liste."""
    listed = {k for ks in all_keys().values() for k in ks}
    rng = random.Random(7)
    start = datetime(1801, 1, 1, tzinfo=timezone.utc)
    for _ in range(600):
        c = build_chart(start + timedelta(days=rng.uniform(0, 597 * 365.25)))
        k = chart_keys(c)
        flat = [k[x] for x in ("type", "authority", "profile", "definition", "cross")] + \
            [x for cat in ("centers", "gates", "lines", "channels", "variables") for x in k[cat]]
        assert set(flat) <= listed, set(flat) - listed


def test_cross_key_follows_the_cross_name():
    c = build_chart(local_to_utc(REFERENCE_1["local"], REFERENCE_1["tz"]).utc)
    assert c.cross == "Left Angle Cross of the Plane 2"
    assert cross_key(c.personality["sun"].gate, "4/1").startswith("cross.juxtaposition.")
    assert cross_key(c.personality["sun"].gate, "1/3").startswith("cross.right-angle.")


def test_no_interpretation_text_in_the_manifest():
    """Le fichier ne contient que des clés (et des compteurs), aucun texte."""
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert set(m) == {"version", "description", "counts", "keys"}
    assert all(isinstance(v, list) and all(KEY_RE.match(x) for x in v) for v in m["keys"].values())


def test_chart_route_content_keys_option():
    code, r = call({**API_REF_1, "include_svg": False})
    assert "content_keys" not in r
    code, r = call({**API_REF_1, "include_svg": False, "content_keys": True})
    assert code == 200 and r["content_keys"]["profile"] == "profile.5-1"
    code, r = call({**API_REF_1, "content_keys": "oui"})
    assert code == 400
