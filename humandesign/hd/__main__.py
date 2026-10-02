# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

import argparse
import json
import sys
from datetime import datetime, timezone

from . import data as D
from .chart import build_chart, summary_fr
from .svg import render_svg
from .timeutil import Place, geocode, local_to_utc, timezone_at


def main(argv=None):
    p = argparse.ArgumentParser(prog="hd", description="Moteur de calcul Human Design (Swiss Ephemeris)")
    p.add_argument("--date", required=True, help="Date de naissance AAAA-MM-JJ")
    p.add_argument("--time", required=True, help="Heure locale HH:MM[:SS]")
    p.add_argument("--place", help="Lieu (géocodé via OpenStreetMap), ex. 'Lyon, France'")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--tz", help="Fuseau IANA, ex. Europe/Paris (sinon déduit des coordonnées)")
    p.add_argument("--utc", action="store_true", help="L'heure fournie est déjà en UTC")
    p.add_argument("--fold", type=int, default=0, choices=[0, 1],
                   help="Heure ambiguë au changement d'heure : 0 = 1re occurrence, 1 = 2e")
    p.add_argument("--name", default="")
    p.add_argument("--svg", help="Fichier SVG de sortie")
    p.add_argument("--json", help="Fichier JSON de sortie")
    a = p.parse_args(argv)

    t = a.time if a.time.count(":") == 2 else a.time + ":00"
    naive = datetime.fromisoformat(f"{a.date}T{t}")
    meta = {}

    if a.utc:
        birth_utc = naive.replace(tzinfo=timezone.utc)
        meta["local"] = f"{naive:%d/%m/%Y %H:%M}"
        meta["tz"], meta["offset"] = "UTC", "+0"
    else:
        if a.lat is not None and a.lon is not None:
            place = Place(a.place or f"{a.lat}, {a.lon}", a.lat, a.lon, a.tz or timezone_at(a.lat, a.lon))
        elif a.place:
            place = geocode(a.place)
            if place.alternatives:
                print("ATTENTION : lieu ambigu, autre(s) fuseau(x) possible(s) :",
                      "; ".join(place.alternatives), file=sys.stderr)
            if a.tz:
                place.tz = a.tz
        elif a.tz:
            place = Place("", 0, 0, a.tz)
        else:
            p.error("indiquer --place, --lat/--lon, --tz ou --utc")
        rt = local_to_utc(naive, place.tz, a.fold)
        if rt.warning:
            print("ATTENTION :", rt.warning, file=sys.stderr)
        birth_utc = rt.utc
        meta.update(local=f"{naive:%d/%m/%Y %H:%M}", tz=place.tz, place=place.name,
                    lat=place.lat, lon=place.lon, dst=rt.dst,
                    offset=f"{rt.utc_offset_hours:+g}")

    c = build_chart(birth_utc, a.name, meta)

    print(f"Naissance UTC : {c.birth_utc:%Y-%m-%d %H:%M:%S}   Design UTC : {c.design_utc:%Y-%m-%d %H:%M:%S}")
    if meta.get("tz") and meta["tz"] != "UTC":
        print(f"Fuseau : {meta['tz']} (UTC{meta['offset']}, heure d'été : {'oui' if meta['dst'] else 'non'})")
    print(f"\n{'':12} {'Design':>10}   {'Personnalité':>12}")
    for pl in D.PLANETS:
        print(f"{D.PLANET_NAMES_FR[pl]:12} {c.design[pl].label:>10}   {c.personality[pl].label:>12}")
    print()
    for line in summary_fr(c):
        print(line)
    print("Canaux :", ", ".join(f"{x}-{y}" for x, y in c.channels) or "aucun")
    print("Centres définis :", ", ".join(D.CENTER_NAMES_FR[x] for x in c.defined_centers) or "aucun")
    print("Variables :", ", ".join(f"{D.VARIABLE_LABELS[k]} {v}" for k, v in c.variables.items()))

    if a.svg:
        with open(a.svg, "w", encoding="utf-8") as f:
            f.write(render_svg(c))
        print("SVG :", a.svg)
    if a.json:
        d = c.to_dict()
        for side in ("personality", "design"):
            d[side] = {k: {**v, "label": f"{v['gate']}.{v['line']}{v['fixing']}"} for k, v in d[side].items()}
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2, default=str)
        print("JSON :", a.json)


if __name__ == "__main__":
    main()
