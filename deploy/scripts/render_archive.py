#!/usr/bin/env python3
"""Genere une page de scoreboard autonome a partir du JSON de l'API CTFd.

Le scoreboard de CTFd est rendu cote client : la page HTML servie ne contient
aucune ligne, elles arrivent par un appel a /api/v1/scoreboard. Un simple
miroir wget produit donc une page qui affiche « Scoreboard is empty » pour
toujours, puisque l'API n'existe plus une fois les instances detruites.

On fige donc les donnees dans le HTML.
"""

import html
import json
import pathlib
import sys


def render(directory: pathlib.Path, label: str) -> None:
    payload = json.loads((directory / "scoreboard.json").read_text())
    standings = payload.get("data", payload) or []

    rows = []
    for rank, entry in enumerate(standings, start=1):
        name = html.escape(str(entry.get("name", "?")))
        score = html.escape(str(entry.get("score", 0)))
        rows.append(
            f"<tr><td class='rank'>{rank}</td><td>{name}</td>"
            f"<td class='score'>{score}</td></tr>"
        )

    if not rows:
        rows.append("<tr><td colspan='3'>Aucun classement enregistre.</td></tr>")

    title = f"CTF — {html.escape(label)}"
    page = f"""<!doctype html>
<html lang="fr">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.5 system-ui, sans-serif; margin: 0; padding: 2rem 1rem;
         max-width: 46rem; margin-inline: auto; }}
  h1 {{ font-size: 1.4rem; margin-bottom: .25rem; }}
  p.meta {{ opacity: .7; margin-top: 0; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; }}
  th, td {{ text-align: left; padding: .5rem .6rem; border-bottom: 1px solid #8883; }}
  .rank {{ width: 3rem; opacity: .6; }}
  .score {{ text-align: right; font-variant-numeric: tabular-nums; }}
  a {{ color: inherit; }}
</style>
<h1>{title}</h1>
<p class="meta">Classement fige a la cloture de la phase. Les comptes et les
instances de cette edition n'existent plus.</p>
<table>
  <thead><tr><th class="rank">#</th><th>Equipe</th><th class="score">Score</th></tr></thead>
  <tbody>
    {"".join(rows)}
  </tbody>
</table>
<p><a href="../">Toutes les editions</a></p>
</html>
"""
    (directory / "index.html").write_text(page, encoding="utf-8")
    print(f"  {len(standings)} equipe(s) figee(s) dans index.html")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: render_archive.py <dossier> <label>")
    render(pathlib.Path(sys.argv[1]), sys.argv[2])
