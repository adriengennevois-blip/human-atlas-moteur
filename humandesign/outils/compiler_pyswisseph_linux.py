# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Fabrique pyswisseph pour un serveur Linux sans compilateur (o2switch).

pyswisseph n'existe pas en version précompilée pour Linux sur PyPI, et o2switch
interdit le compilateur C. On le compile donc depuis un Mac (ou n'importe quel
ordinateur) avec zig, qui sait produire un module Linux, puis on l'emballe en
paquet « wheel » que pip installe sur le serveur sans rien compiler.

Seul le cœur de la Swiss Ephemeris est compilé (libswe + module Python) : les
extras de pyswisseph (base SQLite, atlas « swephelp ») ne servent pas au moteur.

Prérequis :
    pip install ziglang
    # en-têtes Python du serveur (même version que l'application, ici 3.12) :
    ssh <compte>@<serveur> 'tar czf - -C /opt/alt/python312/include python3.12' > pyinc.tgz
    mkdir pyinc && tar xzf pyinc.tgz -C pyinc

Usage :
    python outils/compiler_pyswisseph_linux.py --include pyinc/python3.12 --sortie dist/

Puis, sur le serveur (dans l'environnement de l'application) :
    pip install pyswisseph-2.10.3.2-cp312-cp312-linux_x86_64.whl
    pip install -r requirements.txt
"""

import argparse
import base64
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "2.10.3.2"
PY_TAG = "cp312"
# glibc 2.17 : le module fonctionne sur tous les Linux depuis 2014 (o2switch : glibc 2.28).
TARGET = "x86_64-linux-gnu.2.17"
LIBSWE = ["swecl", "swedate", "swehel", "swehouse", "swejpl", "swemmoon", "swemplan", "sweph", "swephlib"]


def _sdist(dest: Path) -> Path:
    """Télécharge les sources officielles depuis PyPI et vérifie leur empreinte SHA-256."""
    with urllib.request.urlopen(f"https://pypi.org/pypi/pyswisseph/{VERSION}/json", timeout=30) as r:
        info = json.load(r)
    sdist = next(u for u in info["urls"] if u["packagetype"] == "sdist")
    with urllib.request.urlopen(sdist["url"], timeout=120) as r:
        data = r.read()
    if hashlib.sha256(data).hexdigest() != sdist["digests"]["sha256"]:
        raise SystemExit("empreinte SHA-256 des sources incorrecte : téléchargement refusé")
    archive = dest / sdist["filename"]
    archive.write_bytes(data)
    with tarfile.open(archive) as t:
        t.extractall(dest, filter="data")
    return next(p for p in dest.iterdir() if p.is_dir() and p.name.startswith("pyswisseph-"))


def _compile(src: Path, include: Path, so: Path) -> None:
    sources = ["pyswisseph.c"] + [f"libswe/{n}.c" for n in LIBSWE]
    subprocess.run([sys.executable, "-m", "ziglang", "cc", "-target", TARGET, "-shared", "-fPIC", "-O2",
                    "-std=c99", "-D_GNU_SOURCE", "-DNDEBUG", "-DPYSWE_USE_SWEPHELP=0", "-Wno-everything",
                    "-Ilibswe", f"-I{include.resolve()}", *sources, "-lm", "-o", str(so.resolve())],
                   cwd=src, check=True)


def _wheel(so: Path, license_file: Path, out_dir: Path) -> Path:
    dist_info = f"pyswisseph-{VERSION}.dist-info"
    files = {
        so.name: so.read_bytes(),
        f"{dist_info}/METADATA": (
            f"Metadata-Version: 2.1\nName: pyswisseph\nVersion: {VERSION}\n"
            "Summary: Python extension to the Swiss Ephemeris\n"
            "License: AGPL-3.0-or-later (Swiss Ephemeris (c) Astrodienst AG)\n\n"
            "Compilé pour Human Atlas avec zig (libswe seule, sans swephelp).\n").encode(),
        f"{dist_info}/WHEEL": (f"Wheel-Version: 1.0\nGenerator: human-atlas-zig\nRoot-Is-Purelib: false\n"
                               f"Tag: {PY_TAG}-{PY_TAG}-linux_x86_64\n").encode(),
        f"{dist_info}/LICENSE.txt": license_file.read_bytes(),
        f"{dist_info}/top_level.txt": b"swisseph\n",
    }
    record = []
    for path, data in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        record.append(f"{path},sha256={digest},{len(data)}")
    record.append(f"{dist_info}/RECORD,,")
    files[f"{dist_info}/RECORD"] = ("\n".join(record) + "\n").encode()

    out = out_dir / f"pyswisseph-{VERSION}-{PY_TAG}-{PY_TAG}-linux_x86_64.whl"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path, data in files.items():
            z.writestr(path, data)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--include", required=True, type=Path, help="dossier des en-têtes Python du serveur (python3.12)")
    p.add_argument("--sortie", default=Path("dist"), type=Path, help="dossier où écrire le .whl")
    a = p.parse_args(argv)
    if not (a.include / "Python.h").exists() or not (a.include / "pyconfig.h").exists():
        p.error(f"{a.include} ne contient pas Python.h et pyconfig.h")
    a.sortie.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src = _sdist(tmp)
        so = tmp / f"swisseph.cpython-{PY_TAG[2:]}-x86_64-linux-gnu.so"
        _compile(src, a.include, so)
        print(_wheel(so, src / "LICENSE.txt", a.sortie))


if __name__ == "__main__":
    main()
