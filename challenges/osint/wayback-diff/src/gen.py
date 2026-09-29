"""Generate a Wayback-style bundle of HTML snapshots of a homepage.

Between two consecutive captures, a developer comment carrying a base64 recovery
token was published and then scrubbed. Diffing consecutive snapshots reveals the
deleted line; base64-decoding it yields the flag. Other comments/tokens persist
across all snapshots (decoys that are never removed).

Run:  python3 gen.py   (writes snapshot_*.html to the challenge root)
"""

import base64
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FLAG = "NCTF{wayback_diff_scrubbed_dev_comment}"
TOKEN_B64 = base64.b64encode(FLAG.encode()).decode()

# A decoy base64 present in EVERY snapshot (never removed) -> not the answer.
DECOY_B64 = base64.b64encode(b"analytics-site-id-4471").decode()


def page(news: str, extra_head: str = "", extra_body: str = "") -> str:
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>CERT.tg - Portail national de cybersecurite</title>
<!-- build: analytics token {DECOY_B64} -->
{extra_head}</head>
<body>
<header><h1>CERT.tg</h1></header>
<main>
<section class="news"><p>{news}</p></section>
{extra_body}</main>
<footer><p>(c) 2021 CERT.tg - Lome</p></footer>
</body>
</html>
"""


SNAPSHOTS = [
    (
        "snapshot_2021-02-10.html",
        page("Lancement du portail national de cybersecurite."),
    ),
    (
        "snapshot_2021-03-05.html",
        page("Campagne de sensibilisation au phishing."),
    ),
    (
        # secret published here by mistake
        "snapshot_2021-03-19.html",
        page(
            "Maintenance planifiee ce week-end.",
            extra_head=f"<!-- TODO remove before prod: recovery={TOKEN_B64} -->\n",
        ),
    ),
    (
        # secret scrubbed here
        "snapshot_2021-04-02.html",
        page("Nouveau formulaire de signalement en ligne."),
    ),
    (
        "snapshot_2021-05-14.html",
        page("Bilan du premier trimestre disponible."),
    ),
]


def main() -> None:
    for fname, html in SNAPSHOTS:
        with open(os.path.join(ROOT, fname), "w") as fh:
            fh.write(html)
    print(f"wrote {len(SNAPSHOTS)} snapshots")


if __name__ == "__main__":
    main()
