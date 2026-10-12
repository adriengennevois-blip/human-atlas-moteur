# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

from hd.signup import signup_result

from .test_reference import REFERENCE_1, REFERENCE_3, REFERENCE_4, REFERENCE_5, REFERENCE_2

import pytest


@pytest.mark.parametrize(
    "ref", [REFERENCE_1, REFERENCE_2, REFERENCE_3, REFERENCE_4, REFERENCE_5],
    ids=["reference-1", "reference-2", "reference-3", "reference-4", "reference-5"],
)
def test_signup_result_matches_engine(ref):
    d = ref["local"]
    r = signup_result(
        date=d.strftime("%Y-%m-%d"), time=d.strftime("%H:%M"), tz=ref["tz"],
        extended=True,
    )
    assert r["type"] == ref["type"]
    assert r["authority"] == ref["authority"]
    assert r["profile"] == ref["profile"]
    assert r["cross"] == ref["cross"]
    assert r["channels"] == [f"{a}-{b}" for a, b in ref["channels"]]
    assert r["time_warning"] is None


def test_signup_result_minimal_shape():
    r = signup_result(date="1999-09-20", time="08:26", tz="Europe/Paris")
    assert set(r) == {
        "type", "type_fr", "authority", "authority_fr",
        "profile", "profile_label", "birth_utc", "time_warning",
    }
    assert r["type"] == "Generator"
    assert r["profile_label"].startswith("5/1 (")


def test_signup_result_with_birth_utc():
    from datetime import datetime, timezone

    r = signup_result(birth_utc=datetime(1999, 9, 20, 6, 26, tzinfo=timezone.utc))
    assert r["type"] == "Generator"


def test_signup_result_requires_enough_input():
    with pytest.raises(Exception):
        signup_result(date="1999-09-20")


def test_manifesting_generator_label_is_m_generateur():
    """Libellé français du type Manifesting Generator : « M-Générateur » (avec l'accent)."""
    from hd.bodygraph import summary_sentence
    from hd.chart import build_chart
    from hd.timeutil import local_to_utc

    d = REFERENCE_3["local"]
    r = signup_result(date=d.strftime("%Y-%m-%d"), time=d.strftime("%H:%M"), tz=REFERENCE_3["tz"])
    assert (r["type"], r["type_fr"]) == ("Manifesting Generator", "M-Générateur")
    c = build_chart(local_to_utc(d, REFERENCE_3["tz"]).utc)
    assert summary_sentence(c) == "M-Générateur à autorité émotionnelle (Plexus solaire), profil 3/5 (Martyr / Hérétique)"
