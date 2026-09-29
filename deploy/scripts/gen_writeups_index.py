#!/usr/bin/env python3
"""Regenerate challenges/WRITEUPS.md — the human index of jeopardy writeups.

One table per category (challenge · points · type · writeup link · résumé),
built from each challenge's challenge.yml. KotH hills (challenges/koth/, no
challenge.yml) are intentionally excluded — they are scored via Awards, see
deploy/koth-ops.md. Idempotent. Run prettier on the result afterwards
(the repo formats `**/*.md`): `prettier --write challenges/WRITEUPS.md`.

    python3 deploy/scripts/gen_writeups_index.py            # write the index
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHALLENGES = os.path.join(ROOT, "challenges")
INDEX = os.path.join(CHALLENGES, "WRITEUPS.md")
SUMMARY_LEN = 74

_MD = re.compile(r"[*_`>#]+")


def _summary(desc):
    """First meaningful line of the description, flattened for a table cell."""
    for raw in (desc or "").splitlines():
        line = _MD.sub("", raw).replace("|", "/").strip()
        if line and not line.lower().startswith("flag format"):
            return (line[:SUMMARY_LEN] + "…") if len(line) > SUMMARY_LEN else line
    return ""


def collect():
    cats = {}
    for y in sorted(glob.glob(os.path.join(CHALLENGES, "*/*/challenge.yml"))):
        d = os.path.dirname(y)
        doc = yaml.safe_load(open(y, encoding="utf-8")) or {}
        cat = doc.get("category") or os.path.basename(os.path.dirname(d))
        cats.setdefault(cat, []).append(
            {
                "slug": os.path.basename(d),
                "name": doc.get("name") or os.path.basename(d),
                "value": doc.get("value"),
                "type": doc.get("type") or "dynamic",
                "summary": _summary(doc.get("description")),
            }
        )
    for chals in cats.values():
        chals.sort(key=lambda c: c["name"].lower())
    return cats


def render(cats):
    total = sum(len(v) for v in cats.values())
    out = [
        "# Index des writeups — NCTF",
        "",
        f"**{total} challenges** répartis sur **{len(cats)} catégories**. Chaque "
        "challenge servi/statique a son writeup dans son dossier `solution/`.",
        "",
        "> Les collines King-of-the-Hill (`challenges/koth/`) sont scorées par le "
        "plugin `koth` (Awards) et ne figurent pas dans ce tableau jeopardy ; voir "
        "`deploy/koth-ops.md`.",
        "",
    ]
    for cat in sorted(cats):
        chals = cats[cat]
        out += [f"## {cat} ({len(chals)})", ""]
        out += [
            "| challenge | pts | type | writeup | résumé |",
            "| --- | --- | --- | --- | --- |",
        ]
        for c in chals:
            pts = c["value"] if c["value"] is not None else ""
            link = f"[writeup]({cat}/{c['slug']}/solution/)"
            out.append(
                f"| `{c['name']}` | {pts} | {c['type']} | {link} | {c['summary']} |"
            )
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main(argv=None):
    cats = collect()
    open(INDEX, "w", encoding="utf-8").write(render(cats))
    print(f"écrit {INDEX} ({sum(len(v) for v in cats.values())} challenges)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
