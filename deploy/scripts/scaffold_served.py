#!/usr/bin/env python3
"""Scaffold a served (per-team) challenge skeleton — the boilerplate every
served challenge shares, so the build session writes only the vulnerability and
the solver, not the ten wrapper files, 300 times over.

What it stamps (matching the cve/hookrelay convention):

    challenges/<cat>/<slug>/
      challenge.yml        type: team_instance, flags: team_hmac <cat>-<slug>,
                           dynamic scoring, paid-hint stubs
      Dockerfile           ctf-<cat>-<slug>:latest, drop privilege after boot
      docker-compose.yml   local build + smoke notes
      flag.py              CHALLENGE_ID = "<cat>-<slug>" (per-team derivation)
      app/app.py           **NON-FUNCTIONAL STUB** — a placeholder service with a
                           clearly-marked TODO where the vulnerability goes
      app/requirements.txt
      app/entrypoint.sh    writes the per-team flag, drops to appuser
      solution/README.md   stub
      solution/solve.py    stub: python3 solve.py http://HOST:PORT -> NCTF{...}

IMPORTANT: a scaffolded challenge is a **stub**, not a shippable challenge. Its
app serves a placeholder; it has no real vulnerability and its solver does not
solve anything yet. `make preflight` / `make local-playtest` will (correctly)
flag it until the build session fills in the vuln + solver. It exists to remove
boilerplate, not to inflate the challenge count.

Single or batch:

    python3 deploy/scripts/scaffold_served.py \\
        --name web/token-forge --points 500 --title "Token Forge" \\
        --summary "A session service with a forgeable token."

    # batch from a manifest (one challenge per row):
    python3 deploy/scripts/scaffold_served.py --manifest chains.yml

Manifest row keys: name (cat/slug, required), points, title, summary, cve,
internal_port. See deploy/challenge-chains-blueprint.md for the backlog.
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHALLENGES = os.path.join(ROOT, "challenges")

try:
    import yaml
except ImportError:
    yaml = None


def cid_of(name):
    cat, slug = name.split("/", 1)
    return cat, slug, f"{cat}-{slug}"


FLAG_PY = '''#!/usr/bin/env python3
"""Per-challenge flag derivation for `{cid}` (served, per-team).

The instancier injects FLAG / CHALLENGE_SECRET; the flag body is
CHALLENGE_SECRET[:24], i.e. FLAG == "NCTF{{" + CHALLENGE_SECRET[:24] + "}}".
Off-arena, a LOCAL DEV fallback derives from TEAM_SECRET so the image still runs.
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "{cid}"


def flag(team_secret: str) -> str:
    digest = hmac.new(
        team_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256
    ).hexdigest()
    return "NCTF{{" + digest[:24] + "}}"


def get_flag() -> str:
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag
    cs = os.environ.get("CHALLENGE_SECRET")
    if cs:
        return "NCTF{{" + cs[:24] + "}}"
    return flag(os.environ.get("TEAM_SECRET", "local-dev-secret"))


if __name__ == "__main__":
    print(flag(sys.argv[1]) if len(sys.argv) > 1 else get_flag())
'''

APP_PY = '''#!/usr/bin/env python3
"""{title} -- SERVED CHALLENGE STUB.

NON-FUNCTIONAL: this is a scaffold. Replace the placeholder below with the real
vulnerable service. The flag lives in /flag.txt (written by entrypoint.sh from
get_flag()); it must be reachable ONLY through the intended vulnerability, never
served by a route.

Build contract (see deploy/challenge-chains-blueprint.md):
  * success oracle is server-side -- the flag appears only after a real effect;
  * for a multi-stage chain, stage N's unlock is emitted only as an effect of
    stage N-1 (audit line, minted credential, revealed endpoint);
  * self-contained read channel (no attacker callback server).
"""
import os

from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return (
        "<h1>{title}</h1><p>Scaffold stub. TODO: implement the vulnerability "
        "for challenge <code>{cid}</code>.</p>"
    )


# TODO: the vulnerable route(s) go here. The flag is /flag.txt, readable only via
# the intended exploit. Do not add a route that serves it directly.


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
'''

REQS = "Flask==3.0.3\nWerkzeug==3.0.3\n"

ENTRY = """#!/bin/sh
# Boot the {cid} service. Runs briefly as root to write this instance's flag,
# then drops to the unprivileged app user to serve HTTP.
set -e

python3 -c 'from flag import get_flag; print(get_flag())' > /flag.txt
chmod 0644 /flag.txt

exec su-exec appuser python3 /app/app.py
"""

DOCKERFILE = """# ctf-{cid}:latest  (SERVED CHALLENGE STUB -- implement the vuln before shipping)
FROM python:3.12-alpine

RUN apk add --no-cache su-exec

WORKDIR /app
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app/ /app/
COPY flag.py /app/flag.py
RUN chmod +x /app/entrypoint.sh
RUN adduser -D -H appuser

EXPOSE {port}

# Dev default only; the instancier injects FLAG / CHALLENGE_SECRET in production.
ENV TEAM_SECRET=devsecret

ENTRYPOINT ["/app/entrypoint.sh"]
"""

COMPOSE = """# Local run notes for {cid} (STUB).
#   docker build -t ctf-{cid}:latest .
#   docker compose up
#   # browse http://localhost:{port}/
services:
  {cid}:
    image: ctf-{cid}:latest
    build: .
    ports:
      - "{port}:{port}"
    environment:
      TEAM_SECRET: "devsecret"
    restart: unless-stopped
"""

CHALLENGE_YML = """name: {slug}
author: ctf-2026
category: {cat}
type: team_instance
description: |
  {summary}

  This instance's flag is on the service's filesystem, served by no route.
  Exploit the service to read it.

  Stuck? Hints are available (they cost a few points).

  Flag format: `NCTF{{...}}`

# Dynamic scoring.
value: {points}
extra:
  docker_image: ctf-{cid}:latest
  internal_port: {port}
  initial: {points}
  decay: 25
  minimum: 100

# SERVED challenge; per-team flag, no static flag ships here.
flags:
  - type: team_hmac
    content: {cid}

# Progressive, point-costing hints. Fill these when the vuln is implemented; the
# CVE id (if any) goes in a paid hint, never in the description.
hints:
  - content: >-
      TODO: cheap hint narrowing the vulnerability class.
    cost: 20
    key: h1
  - content: >-
      TODO: dearer hint (mechanism / advisory id / patch diff).
    cost: 40
    key: h2
    requirements: [h1]

tags:
  - {cat}
{cve_tag}
# challenge-id (HMAC / requirements wiring): {cid}
connection_info: "http://{{host}}:{{port}}/  (per-team instance; use the 'launch' button)"

state: hidden  # STUB -- flip to visible once the vuln + solver are implemented and Lot-5 verified
version: "0.1"
"""

SOLUTION_README = """# {cid} — solution (STUB)

**Category** {cat} · **Value** {points} · **Served** yes (per-team flag)

TODO: document the vulnerability, the intended path, and the read channel.

## Reference solver

```
python3 solution/solve.py http://HOST:PORT   # -> NCTF{{...}}
```

## Verification status

STUB. Not implemented. Live end-to-end exploit is a Lot 5 rehearsal gate (Docker).
"""

SOLVE_PY = '''#!/usr/bin/env python3
"""Reference solver for {cid} -- STUB. TODO: implement the exploit chain and
print the recovered flag.

    python3 solve.py http://HOST:PORT
"""
import sys


def solve(base):
    raise SystemExit("solver not implemented for {cid}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
'''


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def scaffold(
    name, points=500, title=None, summary=None, cve=None, port=8080, force=False
):
    if "/" not in name or name.count("/") != 1:
        raise SystemExit(f"--name must be cat/slug, got {name!r}")
    cat, slug, cid = cid_of(name)
    if not re.fullmatch(r"[a-z0-9-]+", cat) or not re.fullmatch(r"[a-z0-9-]+", slug):
        raise SystemExit(f"cat/slug must be [a-z0-9-]: {name!r}")
    cdir = os.path.join(CHALLENGES, cat, slug)
    if os.path.exists(cdir) and not force:
        print(f"skip (exists): {name}")
        return False
    title = title or slug.replace("-", " ").title()
    summary = summary or f"A served challenge: {title}."
    cve_tag = "  - cve\n" if cve else ""
    ctx = {
        "cat": cat,
        "slug": slug,
        "cid": cid,
        "points": points,
        "title": title,
        "summary": summary,
        "port": port,
        "cve_tag": cve_tag,
    }
    write(os.path.join(cdir, "flag.py"), FLAG_PY.format(**ctx))
    write(os.path.join(cdir, "app", "app.py"), APP_PY.format(**ctx))
    write(os.path.join(cdir, "app", "requirements.txt"), REQS)
    write(os.path.join(cdir, "app", "entrypoint.sh"), ENTRY.format(**ctx))
    write(os.path.join(cdir, "Dockerfile"), DOCKERFILE.format(**ctx))
    write(os.path.join(cdir, "docker-compose.yml"), COMPOSE.format(**ctx))
    write(os.path.join(cdir, "challenge.yml"), CHALLENGE_YML.format(**ctx))
    write(os.path.join(cdir, "solution", "README.md"), SOLUTION_README.format(**ctx))
    write(os.path.join(cdir, "solution", "solve.py"), SOLVE_PY.format(**ctx))
    print(f"scaffolded (STUB): {name}  [ctf-{cid} :{port} {points}pt]")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--name", help="cat/slug")
    ap.add_argument("--points", type=int, default=500)
    ap.add_argument("--title")
    ap.add_argument("--summary")
    ap.add_argument(
        "--cve", help="tag as cve-anchored (id goes in a paid hint, not here)"
    )
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument(
        "--manifest",
        help="YAML list of rows: name, points, title, summary, cve, internal_port",
    )
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)

    made = 0
    if a.manifest:
        if yaml is None:
            sys.exit("pip install pyyaml for --manifest")
        rows = yaml.safe_load(open(a.manifest, encoding="utf-8")) or []
        for row in rows:
            made += scaffold(
                row["name"],
                points=int(row.get("points", 500)),
                title=row.get("title"),
                summary=row.get("summary"),
                cve=row.get("cve"),
                port=int(row.get("internal_port", 8080)),
                force=a.force,
            )
    elif a.name:
        made += scaffold(a.name, a.points, a.title, a.summary, a.cve, a.port, a.force)
    else:
        ap.error("give --name or --manifest")
    print(
        f"\n{made} scaffolded. Each is a STUB (state: hidden) -- implement the vuln + solver, then flip to visible and Lot-5 verify."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
