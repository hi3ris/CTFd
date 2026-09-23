#!/usr/bin/env python3
"""Compose a large backlog of DISTINCT served combination-vulnerability challenge
specs and emit a scaffolder manifest.

Each row is a served (per-team) challenge designed as a 2-3 vulnerability chain:
a real category, a real chain of vuln classes, a unique themed context. Summaries
are design-level (the chain of classes), never a payload. This is the *design*
runway; scaffold_served.py stamps each as a STUB (state: hidden), and the build
session implements the vuln + solver and verifies under Docker before shipping.

    python3 deploy/scripts/gen_backlog.py --count 256 --out deploy/backlog-gen.yml
    python3 deploy/scripts/scaffold_served.py --manifest deploy/backlog-gen.yml

Deterministic: the same taxonomy always yields the same ordered set, so re-runs
are stable and skip already-scaffolded slots.
"""
import argparse
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHALLENGES = os.path.join(ROOT, "challenges")

# Per category: chain patterns (class combos, design-level) and themed contexts.
# name = <category>/<theme>-<tag>; summary = the chain of vuln classes.
TAXO = {
    "web": {
        "themes": [
            "ledger",
            "hrportal",
            "shipyard",
            "invoicer",
            "forum",
            "cms",
            "wiki",
            "shopfront",
            "helpdesk",
            "boards",
            "notary",
            "planner",
        ],
        "chains": [
            (
                "authbypass",
                "Contournement d'auth -> IDOR -> mass-assignment vers rôle admin.",
                450,
            ),
            (
                "ssrf-deser",
                "SSRF -> service RPC interne -> désérialisation non sûre -> exécution.",
                500,
            ),
            (
                "smuggle",
                "Request smuggling -> empoisonnement de cache -> contournement d'auth.",
                500,
            ),
            (
                "uploadssrf",
                "Contournement d'upload -> SSRF via le rendu -> lecture metadata.",
                450,
            ),
            (
                "jwtconf",
                "Confusion d'algorithme JWT -> forge -> endpoint interne exposé.",
                400,
            ),
            ("xxe", "XXE -> SSRF -> lecture de fichier interne.", 450),
            ("protopoll", "Prototype pollution -> gadget -> exécution.", 500),
            (
                "sqli2",
                "Injection SQL de second ordre -> contournement d'auth -> action admin.",
                450,
            ),
        ],
    },
    "cloud": {
        "themes": [
            "metrics",
            "billing",
            "registry",
            "gateway",
            "backup",
            "cdn",
            "identity",
            "queue",
            "artifacts",
            "secrets",
        ],
        "chains": [
            ("imds", "SSRF -> IMDS -> assume-role -> lecture d'objet privé.", 500),
            ("oidc", "Mauvaise config OIDC -> jeton forgé -> API privilégiée.", 500),
            ("prefix", "Préfixe public -> credential fuité -> escalade de rôle.", 450),
            (
                "envexec",
                "Injection d'env dans une fonction -> exécution -> vol de secret.",
                500,
            ),
            (
                "presign",
                "Abus d'URL pré-signée -> écriture d'objet -> exécution au déploiement.",
                500,
            ),
        ],
    },
    "pwn": {
        "themes": [
            "relaybox",
            "keyvault",
            "meshd",
            "brokerd",
            "sensorhub",
            "authd",
            "cachesrv",
            "logd",
            "parserd",
            "queued",
        ],
        "chains": [
            ("heap", "Reverse d'un protocole -> overflow de tas -> shell.", 550),
            ("fmt", "Fuite d'info -> format string -> ROP -> lecture du flag.", 500),
            (
                "uaf",
                "Use-after-free -> primitive d'écriture -> détournement de flux.",
                550,
            ),
            (
                "sandbox",
                "Bug logique d'un bac à sable -> évasion -> exécution hôte.",
                600,
            ),
            ("canary", "Fuite de canari -> overflow -> chaîne ROP -> exécution.", 500),
        ],
    },
    "reverse": {
        "themes": ["vmcore", "licensed", "packedsvc", "protod", "firmwarelet"],
        "chains": [
            (
                "vmesc",
                "Reverse d'une VM maison -> bug d'instruction -> évasion et exécution.",
                550,
            ),
            (
                "license",
                "Reverse d'un contrôle de licence -> forge -> canal admin.",
                450,
            ),
            ("unpack", "Dépaquetage -> bug de hook -> exécution.", 500),
        ],
    },
    "crypto": {
        "themes": [
            "sealbox",
            "tokenmint",
            "sessiond",
            "notarysvc",
            "vaultkey",
            "signgate",
        ],
        "chains": [
            (
                "padoracle",
                "Oracle de padding -> cookie forgé -> endpoint admin atteint.",
                500,
            ),
            (
                "nonce",
                "Réutilisation de nonce -> récupération de clé -> forge de jeton.",
                450,
            ),
            (
                "kdf",
                "Dérivation de clé faible -> prédiction -> reprise de session.",
                500,
            ),
            (
                "ecb",
                "ECB cut-and-paste -> contournement d'auth -> action privilégiée.",
                450,
            ),
            ("signext", "Extension de hash -> forge -> API privilégiée.", 500),
        ],
    },
    "misc": {
        "themes": ["gluesvc", "relaynode", "ingestd", "bridged", "transcoder"],
        "chains": [
            ("deser", "SSRF -> RPC interne -> désérialisation -> exécution.", 500),
            (
                "protoparse",
                "Parser maison -> état corrompu -> lecture hors-borne.",
                450,
            ),
            ("envreuse", "Fuite d'env -> réutilisation de secret -> exécution.", 450),
        ],
    },
    "supplychain": {
        "themes": ["buildfarm", "pkgproxy", "releaser", "signer", "mirror"],
        "chains": [
            (
                "depconf",
                "Dérive de lockfile -> confusion de dépendance -> hook de build exécuté.",
                550,
            ),
            (
                "artswap",
                "Provenance forgée -> substitution d'artefact -> exécution au déploiement.",
                500,
            ),
            ("postinstall", "Hook post-install -> exécution -> vol de secret.", 500),
        ],
    },
    "ai": {
        "themes": ["deskbot", "triage", "copilotsvc", "retriever"],
        "chains": [
            (
                "inject",
                "Injection indirecte -> abus d'outil -> exfiltration de données.",
                500,
            ),
            (
                "guard",
                "Contournement de garde-fou -> chaîne d'outils -> action privilégiée.",
                550,
            ),
        ],
    },
    "ml": {
        "themes": ["modelhub", "scorer", "trainer", "featurizer"],
        "chains": [
            (
                "pickle",
                "Upload de modèle -> pipeline -> désérialisation pickle -> exécution.",
                500,
            ),
            (
                "poison",
                "Injection dans le pré-traitement -> empoisonnement -> exfiltration.",
                450,
            ),
        ],
    },
    "blockchain": {
        "themes": ["vaultdao", "bridgepool", "lender", "escrowd", "oraclefeed"],
        "chains": [
            ("reentry", "Rejeu de signature -> réentrance -> drain de fonds.", 550),
            (
                "proxy",
                "Collision de storage proxy -> écrasement d'admin -> action.",
                500,
            ),
            ("allowance", "Dérive d'allowance -> approbation -> drain.", 500),
        ],
    },
    "sysadmin": {
        "themes": ["orchestrator", "provisioner", "rotatord", "auditd", "schedd"],
        "chains": [
            (
                "systemd",
                "Injection d'env -> unit systemd -> sudo mal configuré -> root.",
                500,
            ),
            ("cron", "Injection de chemin -> cron -> root.", 450),
            ("cap", "Capability mal configurée -> escalade -> root.", 500),
        ],
    },
}


def existing_names():
    out = set()
    for y in glob.glob(os.path.join(CHALLENGES, "*/*/challenge.yml")):
        d = os.path.dirname(y)
        out.add(os.path.relpath(d, CHALLENGES))
    return out


def generate(count):
    have = existing_names()
    rows = []
    # Round-robin across categories so the backlog stays balanced, not 200 web.
    cats = list(TAXO)
    combos = []
    for cat in cats:
        spec = TAXO[cat]
        for theme in spec["themes"]:
            for tag, summary, points in spec["chains"]:
                name = f"{cat}/{theme}-{tag}"
                combos.append((cat, name, points, summary))
    # interleave by category for balance
    by_cat = {}
    for c in combos:
        by_cat.setdefault(c[0], []).append(c)
    order = []
    while any(by_cat.values()):
        for cat in cats:
            if by_cat.get(cat):
                order.append(by_cat[cat].pop(0))
    for _cat, name, points, summary in order:
        if len(rows) >= count:
            break
        if name in have:
            continue
        rows.append(
            {
                "name": name,
                "points": points,
                "title": name.split("/")[1].replace("-", " ").title(),
                "summary": summary,
            }
        )
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--count", type=int, required=True, help="number of new distinct slots to emit"
    )
    ap.add_argument("--out", required=True, help="manifest path to write (YAML)")
    a = ap.parse_args(argv)
    try:
        import yaml
    except ImportError:
        sys.exit("pip install pyyaml")
    rows = generate(a.count)
    if len(rows) < a.count:
        print(
            f"[warn] taxonomy yields only {len(rows)} new distinct slots (< {a.count}). "
            "Add themes/chains to TAXO for more.",
            file=sys.stderr,
        )
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(
            "# Generated by gen_backlog.py -- DESIGNED served combination-vuln slots.\n"
        )
        fh.write(
            "# Each becomes a STUB (state: hidden) via scaffold_served.py; implement + verify before shipping.\n"
        )
        yaml.safe_dump(
            rows, fh, allow_unicode=True, sort_keys=False, default_flow_style=False
        )
    print(f"wrote {len(rows)} rows to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
