#!/usr/bin/env python3
"""Generate / update the writeups tree the in-app `writeups` plugin reads.

For every challenge, write:

    writeups/<category>/<slug>.md

from that challenge's `solution/README.md` (its author-written writeup), with a
small header (name, category, points, author) prepended and every `NCTF{...}`
redacted to `NCTF{…}`. Idempotent: re-running refreshes the tree in place, so
this is both "écris" and "mets à jour".

    python3 deploy/scripts/sync_writeups.py            # write writeups/ at repo root
    python3 deploy/scripts/sync_writeups.py --out DIR  # elsewhere
    python3 deploy/scripts/sync_writeups.py --prune     # also delete orphans

A challenge whose solution/README.md is a scaffold STUB yields a stub writeup
(marked as such) -- honest: there is no real solution to publish yet.
"""
import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHALLENGES = os.path.join(ROOT, "challenges")
FLAG = re.compile(r"NCTF\{[^}]*\}")

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")


def field(doc, *keys, default=""):
    for k in keys:
        if doc.get(k):
            return doc[k]
    return default


def build(cdir, doc, cat, slug):
    name = field(doc, "name", default=slug)
    pts = doc.get("value") or (doc.get("extra") or {}).get("initial") or "?"
    author = field(doc, "author", default="—")
    readme = os.path.join(cdir, "solution", "README.md")
    if os.path.isfile(readme):
        body = open(readme, encoding="utf-8").read().strip()
    else:
        body = "_Pas encore de writeup pour ce challenge._"
    is_stub = "STUB" in body[:400] or doc.get("state") == "hidden"
    header = f"# {name}\n\n**Catégorie** {cat} · **Points** {pts} · **Auteur** {author}"
    if is_stub:
        header += "\n\n> ⚠️ Challenge non finalisé — writeup provisoire."
    md = header + "\n\n" + FLAG.sub("NCTF{…}", body) + "\n"
    return md


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", default=os.path.join(ROOT, "writeups"))
    ap.add_argument(
        "--prune", action="store_true", help="delete writeups with no challenge"
    )
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)

    written = set()
    n = 0
    for y in sorted(glob.glob(os.path.join(CHALLENGES, "*/*/challenge.yml"))):
        cdir = os.path.dirname(y)
        rel = os.path.relpath(cdir, CHALLENGES)
        cat, slug = rel.split("/", 1)
        if "/" in slug:  # only cat/slug depth
            continue
        try:
            doc = yaml.safe_load(open(y, encoding="utf-8")) or {}
        except Exception as e:
            print(f"[skip] {rel}: {e}", file=sys.stderr)
            continue
        dst = os.path.join(out, cat, slug + ".md")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(build(cdir, doc, cat, slug))
        written.add(os.path.abspath(dst))
        n += 1

    pruned = 0
    if a.prune and os.path.isdir(out):
        for md in glob.glob(os.path.join(out, "*", "*.md")):
            if os.path.abspath(md) not in written:
                os.remove(md)
                pruned += 1

    print(f"wrote {n} writeups to {out}" + (f", pruned {pruned}" if a.prune else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
