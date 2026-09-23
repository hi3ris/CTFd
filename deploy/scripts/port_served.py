#!/usr/bin/env python3
"""Port a verified served-challenge implementation onto its family siblings.

Several served stubs share a vulnerability class with an already-implemented
challenge (e.g. every `*-padoracle` is the padding-oracle class). Because the app
reads its flag from /flag.txt (written by flag.py, whose CHALLENGE_ID is already
per-slug) and the reference solver is URL-driven, porting a class is a faithful
copy: each sibling keeps its own per-team flag.

For each sibling this copies the prototype's app.py / requirements.txt / solve.py,
reuses the prototype's hints, and writes a class writeup adapted to the slug.

    python3 deploy/scripts/port_served.py            # port all mapped siblings
    python3 deploy/scripts/port_served.py --only crypto/sessiond-ecb ...

Idempotent: re-running refreshes the ported files.
"""
import argparse
import glob
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CH = os.path.join(ROOT, "challenges")

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")

# suffix -> prototype "cat/slug" (verified implementations)
PROTO = {
    "ecb": "crypto/sealbox-ecb",
    "kdf": "crypto/kdf-slip",
    "nonce": "crypto/nonce-climb",
    "padoracle": "crypto/oracle-cascade",
    "signext": "crypto/sealbox-signext",
    "jwtconf": "web/jwt-relay",
    "authbypass": "web/forum-authbypass",
    "sqli2": "web/forum-sqli2",
    "oidc": "cloud/oidc-forge",
    "imds": "cloud/backup-imds",
    "prefix": "cloud/backup-prefix",
    "presign": "cloud/backup-presign",
    "envexec": "cloud/backup-envexec",
    "protoparse": "misc/proto-fuzz-live",
}


def challenge_id(cdir):
    m = re.search(
        r'CHALLENGE_ID\s*=\s*"([^"]+)"', open(os.path.join(cdir, "flag.py")).read()
    )
    return m.group(1) if m else None


def match_proto(slug):
    for suf, proto in PROTO.items():
        if slug.endswith("-" + suf) or slug == suf:
            return suf, proto
    return None, None


def hints_block(proto_dir):
    doc = yaml.safe_load(open(os.path.join(proto_dir, "challenge.yml")))
    out = ["hints:"]
    for h in doc.get("hints", []):
        out.append("  - content: >-")
        out.append("      " + " ".join((h.get("content") or "").split()))
        out.append(f"    cost: {h.get('cost', 20)}")
        out.append(f"    key: {h.get('key', 'h1')}")
        if h.get("requirements"):
            out.append(f"    requirements: [{', '.join(h['requirements'])}]")
    return "\n".join(out)


TODO_HINTS = """hints:
  - content: >-
      TODO: cheap hint narrowing the vulnerability class.
    cost: 20
    key: h1
  - content: >-
      TODO: dearer hint (mechanism / advisory id / patch diff).
    cost: 40
    key: h2
    requirements: [h1]"""


def patch_yaml(sib_dir, proto_dir):
    p = os.path.join(sib_dir, "challenge.yml")
    t = open(p, encoding="utf-8").read()
    # Replace the scaffold's exact TODO hints block with the prototype hints.
    # (Literal replace, never a greedy/DOTALL regex that could eat later keys.)
    if TODO_HINTS in t:
        t = t.replace(TODO_HINTS, hints_block(proto_dir), 1)
    t = t.replace(
        "state: hidden  # STUB -- flip to visible once the vuln + solver are"
        " implemented and Lot-5 verified",
        "state: hidden  # IMPLEMENTED + locally verified end-to-end (ported);"
        " flip to visible after Lot-5 Docker rehearsal",
    )
    t = t.replace('version: "0.1"', 'version: "1.0"')
    open(p, "w", encoding="utf-8").write(t)


def write_readme(sib_dir, proto_dir, sib_slug, sib_cid):
    proto_slug = os.path.basename(proto_dir)
    proto_cid = challenge_id(proto_dir)
    body = open(
        os.path.join(proto_dir, "solution", "README.md"), encoding="utf-8"
    ).read()
    body = body.replace(proto_cid, sib_cid).replace(proto_slug, sib_slug)
    # note it is a class variant
    body = body.replace(
        "## Verification status",
        "> Variante de la classe `" + proto_slug + "` (même vulnérabilité, "
        "instance et flag par-équipe distincts).\n\n## Verification status",
        1,
    )
    open(os.path.join(sib_dir, "solution", "README.md"), "w", encoding="utf-8").write(
        body
    )


def port(sib_rel):
    sib_dir = os.path.join(CH, sib_rel)
    slug = sib_rel.split("/")[1]
    suf, proto = match_proto(slug)
    if not proto:
        return f"[skip] {sib_rel}: no prototype match"
    proto_dir = os.path.join(CH, proto)
    proto_base = os.path.basename(proto)
    # copy app + solver verbatim, then adapt the service name string
    for rel in ("app/app.py", "app/requirements.txt", "solution/solve.py"):
        src = os.path.join(proto_dir, rel)
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(os.path.join(sib_dir, rel)), exist_ok=True)
            shutil.copyfile(src, os.path.join(sib_dir, rel))
    appp = os.path.join(sib_dir, "app", "app.py")
    a = open(appp, encoding="utf-8").read().replace(proto_base, slug)
    open(appp, "w", encoding="utf-8").write(a)
    patch_yaml(sib_dir, proto_dir)
    write_readme(sib_dir, proto_dir, slug, challenge_id(sib_dir))
    return f"[ok]   {sib_rel}  <- {proto}"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    if a.only:
        targets = a.only
    else:
        targets = []
        for y in sorted(glob.glob(os.path.join(CH, "*/*/challenge.yml"))):
            raw = open(y).read()
            doc = yaml.safe_load(raw) or {}
            if doc.get("type") != "team_instance":
                continue
            if doc.get("state") != "hidden" or "IMPLEMENTED + locally verified" in raw:
                continue
            rel = os.path.relpath(os.path.dirname(y), CH)
            if match_proto(rel.split("/")[1])[1]:
                targets.append(rel)
    n = 0
    for t in targets:
        line = port(t)
        print(line)
        if line.startswith("[ok]"):
            n += 1
    print(f"\nported {n} siblings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
