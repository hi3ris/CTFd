#!/usr/bin/env python3
"""Reconstruit la page d'accueil listant toutes les editions archivees.

Chaque phase archivee vit sous son propre prefixe site/<phase>-<date>/. Sans
cette page, la racine du site renvoie une erreur et les archives sont
introuvables.
"""

import html
import subprocess
import sys


def editions(bucket: str) -> list[str]:
    out = subprocess.run(
        ["aws", "s3", "ls", f"s3://{bucket}/site/"],
        capture_output=True, text=True, check=True,
    ).stdout
    names = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "PRE":
            names.append(parts[1].rstrip("/"))
    return sorted(names, reverse=True)


def main(bucket: str) -> None:
    names = editions(bucket)
    items = "\n".join(
        f'    <li><a href="{html.escape(n)}/">{html.escape(n)}</a></li>'
        for n in names
    ) or "    <li>Aucune edition archivee.</li>"

    page = f"""<!doctype html>
<html lang="fr">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Archives du CTF</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.5 system-ui, sans-serif; margin: 0; padding: 2rem 1rem;
         max-width: 46rem; margin-inline: auto; }}
  h1 {{ font-size: 1.4rem; }}
  li {{ margin: .4rem 0; }}
</style>
<h1>Archives du CTF</h1>
<p>Classements figes des editions passees.</p>
<ul>
{items}
</ul>
</html>
"""
    with open("/tmp/ctf-site-index.html", "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"  {len(names)} edition(s) listee(s)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: render_index.py <bucket>")
    main(sys.argv[1])
