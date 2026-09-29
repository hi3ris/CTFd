#!/usr/bin/env python3
"""Validation statique de challenges/*/*/challenge.yml (CI et pre-commit).

Regles :
  - YAML lisible, `name`, `category`, `type`, `value`/`extra` presents ;
  - `category` == nom du dossier parent, `name` unique ;
  - un servi (type team_instance) livre Dockerfile + docker-compose.yml +
    flag.py + solution/solve.py des qu'il est marque IMPLEMENTED ;
  - un servi n'est `state: visible` que s'il a passe le Lot-5 (marqueur
    "Lot-5 rehearsal passed" pose par deploy/scripts/lot5.sh --flip) : un
    servi visible sans image exploitable = joueurs bloques.

    python3 deploy/scripts/check_challenges.py            # sortie non nulle si erreur
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CH = ROOT / "challenges"
LOT5_MARK = "Lot-5 rehearsal passed"

errors, warns = [], []
names = {}
n_total = n_served = n_visible_served = 0

for y in sorted(CH.glob("*/*/challenge.yml")):
    rel = y.parent.relative_to(CH).as_posix()
    cat, slug = rel.split("/")
    text = y.read_text(encoding="utf-8")
    try:
        d = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        errors.append(f"{rel}: YAML illisible ({e})")
        continue
    n_total += 1

    for key in ("name", "category", "type"):
        if not d.get(key):
            errors.append(f"{rel}: cle `{key}` manquante")
    if d.get("value") is None and not (d.get("extra") or {}).get("initial"):
        errors.append(f"{rel}: ni `value` ni `extra.initial`")
    if d.get("category") != cat:
        errors.append(f"{rel}: category `{d.get('category')}` != dossier `{cat}`")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        errors.append(f"{rel}: slug non conforme (a-z0-9-)")
    name = d.get("name")
    if name in names:
        errors.append(f"{rel}: name `{name}` deja utilise par {names[name]}")
    names[name] = rel

    if d.get("type") != "team_instance":
        continue
    n_served += 1
    implemented = "IMPLEMENTED" in text
    if implemented:
        for f in ("Dockerfile", "docker-compose.yml", "flag.py", "solution/solve.py"):
            if not (y.parent / f).exists():
                errors.append(f"{rel}: servi IMPLEMENTED sans {f}")
    state = str(d.get("state", "visible")).lower()
    if state == "visible":
        n_visible_served += 1
        if LOT5_MARK not in text:
            if implemented:
                errors.append(
                    f"{rel}: servi `visible` sans passage Lot-5 "
                    f"(deploy/scripts/lot5.sh --flip --only {rel}, ou state: hidden)"
                )
            else:
                # Servi historique (hors harnais Lot-5 : TCP, solveur a l'ancienne
                # interface) : valide par `make local-playtest`, on signale seulement.
                warns.append(
                    f"{rel}: servi historique visible sans marque Lot-5 (playtest)"
                )
    elif not implemented:
        pass  # STUB cache : normal
    elif LOT5_MARK in text:
        warns.append(f"{rel}: marque Lot-5 mais toujours hidden")

print(
    f"{n_total} challenges, {n_served} servis dont {n_visible_served} visibles ; "
    f"{len(errors)} erreur(s), {len(warns)} avertissement(s)"
)
for w in warns:
    print("WARN ", w)
for e in errors:
    print("ERROR", e)
sys.exit(1 if errors else 0)
