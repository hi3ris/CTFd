#!/usr/bin/env python3
"""Generate the challenge name -> author map the hibris challenge board reads.

The CTFd challenge-list API does not expose a challenge's author, so the
"group by author" view on the challenges page reads a static map instead. This
builds it from each challenge.yml's `author` field, keyed by challenge `name`
(the board already has the name, and names are unique across the set).

    python3 deploy/scripts/gen_authors_map.py        # write the JSON in the theme
    python3 deploy/scripts/gen_authors_map.py --check # verify it is up to date

Output: CTFd/themes/hibris/static/js/pages/challenge-authors.json
"""
import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(
    ROOT, "CTFd", "themes", "hibris", "static", "js", "pages", "challenge-authors.json"
)

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")


def build():
    mapping = {}
    for y in sorted(
        glob.glob(os.path.join(ROOT, "challenges", "*", "*", "challenge.yml"))
    ):
        try:
            doc = yaml.safe_load(open(y, encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            continue
        name = doc.get("name")
        if not name:
            continue
        mapping[name] = (doc.get("author") or "").strip() or "—"
    return dict(sorted(mapping.items()))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    mapping = build()
    payload = json.dumps(mapping, ensure_ascii=False, indent=0, sort_keys=True) + "\n"
    if a.check:
        current = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else ""
        if current != payload:
            print(
                "challenge-authors.json is stale; run gen_authors_map.py",
                file=sys.stderr,
            )
            return 1
        print("challenge-authors.json up to date")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(payload)
    print(f"wrote {len(mapping)} name->author entries to {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
