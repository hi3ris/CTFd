#!/usr/bin/env python3
"""Writeups officiels -> pages CTFd (et archive statique S3).

  publish_writeups.py --url https://ctf... --token <jeton admin> --prepare
  publish_writeups.py --url ... --token ... --publish [--force]
  publish_writeups.py --url ... --token ... --unpublish
  publish_writeups.py --static /tmp/ctf-archive/writeups     # HTML autonome (make archive)

Assemble challenges/WRITEUPS.md (l'index) et chaque challenges/<cat>/<slug>/
solution/README.md en pages CTFd Markdown :

  /writeups          index : par categorie, challenge, points, auteur, lien
  /writeups/<cat>    une page par categorie, une section par challenge

Une page par categorie plutot qu'une seule page : `Pages.content` est un TEXT
MariaDB (64 Ko) et les 203 writeups pesent ~360 Ko ; la plus grosse categorie
fait ~36 Ko. Le script refuse une page > 60 Ko.

Les pages sont creees en BROUILLON (`draft`, 404 pour tout le monde) et hors
menu (`hidden`). `--publish` retire le brouillon (l'index entre au menu) et
REFUSE tant que `end` n'est pas passe, sauf `--force` : un writeup publie
pendant l'epreuve, c'est la solution offerte.

Seuls les README sont publies, jamais les solveurs (`solve.py`, ...). Tout
flag `NCTF{...}` reel est remplace par `NCTF{…}` : ceux du challenge.yml du
challenge d'abord (exacts), puis n'importe quel NCTF{...} qui n'est pas deja
le gabarit. Les flags `team_hmac` sont par equipe de toute facon.
"""
import argparse
import html
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHALLENGES = ROOT / "challenges"
INDEX_ROUTE = "writeups"
PLACEHOLDER = "NCTF{…}"
MAX_PAGE_BYTES = 60_000
FLAG_RE = re.compile(r"NCTF\{[^}\n]*\}")
FENCE_RE = re.compile(r"^(```|~~~)")


# --- pure: content ---------------------------------------------------------


def redact(text, flags=()):
    """Exact flags first, then any NCTF{...} that is not already a placeholder."""
    for f in sorted(set(flags), key=len, reverse=True):
        if f:
            text = text.replace(f, PLACEHOLDER)

    def sub(m):
        inner = m.group(0)[5:-1].strip()
        return m.group(0) if inner in ("...", "…", "") else PLACEHOLDER

    return FLAG_RE.sub(sub, text)


def shift_headings(md, n):
    """Push every Markdown heading down by n levels, leaving fenced code alone."""
    out, fenced = [], False
    for line in md.splitlines():
        if FENCE_RE.match(line.strip()):
            fenced = not fenced
        elif not fenced and line.startswith("#"):
            hashes = len(line) - len(line.lstrip("#"))
            if line[hashes : hashes + 1] == " ":
                line = "#" * min(6, hashes + n) + line[hashes:]
        out.append(line)
    return "\n".join(out) + ("\n" if md.endswith("\n") else "")


def _yaml(path):
    try:
        import yaml
    except ImportError:
        sys.exit("pip install pyyaml")
    try:
        return yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}


def load_challenges(root=CHALLENGES, categories=None):
    """[{category, slug, name, author, value, flags, readme}] sorted by category, name."""
    items = []
    for yml in sorted(root.glob("*/*/challenge.yml")):
        d = yml.parent
        cat = d.parent.name
        if categories and cat not in categories:
            continue
        y = _yaml(yml)
        readme = d / "solution" / "README.md"
        items.append(
            {
                "category": y.get("category") or cat,
                "slug": d.name,
                "name": y.get("name") or d.name,
                "author": str(y.get("author") or "").strip('"'),
                "value": y.get("value"),
                "flags": [f for f in (y.get("flags") or []) if isinstance(f, str)],
                "readme": readme.read_text() if readme.exists() else None,
            }
        )
    items.sort(key=lambda c: (c["category"], c["name"].lower()))
    return items


def _by_category(items):
    cats = {}
    for c in items:
        cats.setdefault(c["category"], []).append(c)
    return cats


def _redacted_section(c):
    """The per-challenge block on a category page (anchor, heading, meta, body)."""
    body = [f'<a id="{c["slug"]}"></a>', "", f"## {c['name']}", ""]
    meta = []
    if c["value"] is not None:
        meta.append(f"{c['value']} pts")
    if c["author"]:
        meta.append(f"auteur : {c['author']}")
    if meta:
        body += ["_" + " · ".join(meta) + "_", ""]
    if c["readme"]:
        body += [shift_headings(redact(c["readme"], c["flags"]), 2).rstrip(), ""]
    else:
        body += ["_Pas de writeup publié pour ce challenge._", ""]
    return "\n".join(body)


def _pack_category(cat, chals, budget):
    """Split a category's sections into parts under `budget` bytes.

    Returns (parts, route_of): parts is a list of {route, chals}; route_of maps
    slug -> its part route. The first part keeps the bare `<cat>` route (so
    existing links hold), overflow goes to `<cat>-2`, `<cat>-3`, ...
    """
    groups, cur, cur_size = [], [], 0
    for c in chals:
        sz = len(_redacted_section(c).encode()) + 1
        if sz > budget:
            raise SystemExit(
                f"writeup de `{c['name']}` ({sz} o) dépasse à lui seul la limite de "
                f"page ({MAX_PAGE_BYTES} o = TEXT MariaDB 64 Ko) ; raccourcir son "
                "solution/README.md"
            )
        if cur and cur_size + sz > budget:
            groups.append(cur)
            cur, cur_size = [], 0
        cur.append(c)
        cur_size += sz
    if cur:
        groups.append(cur)
    parts, route_of = [], {}
    for i, grp in enumerate(groups):
        route = f"{INDEX_ROUTE}/{cat}" + ("" if i == 0 else f"-{i + 1}")
        parts.append({"route": route, "chals": grp})
        for c in grp:
            route_of[c["slug"]] = route
    return parts, route_of


def build_pages(items, ctf_name="NCTF26", intro=None):
    """[{route, title, content, menu}] : the index first, then category pages.

    A category that would exceed the DB TEXT cap is split into `<cat>`,
    `<cat>-2`, ... and the index links each challenge to its part.
    """
    cats = _by_category(items)
    n = len(items)
    # Leave headroom for each category page's own header + back-link + joins.
    budget = max(1, MAX_PAGE_BYTES - 800)
    packed = {cat: _pack_category(cat, chals, budget) for cat, chals in cats.items()}

    lines = [
        f"# Writeups {ctf_name}",
        "",
        intro
        or (
            f"**{n} challenges**, **{len(cats)} catégories**. Une page par catégorie "
            "(scindée si besoin), une section par challenge : vulnérabilité, étapes, ce "
            f"qu'il fallait voir. Les flags réels sont masqués (`{PLACEHOLDER}`), les "
            "solveurs ne sont pas publiés."
        ),
        "",
    ]
    for cat, chals in cats.items():
        parts, route_of = packed[cat]
        suffix = f" — {len(parts)} parties" if len(parts) > 1 else ""
        lines += [f"## {cat} ({len(chals)}){suffix}", ""]
        lines += ["| challenge | pts | auteur | writeup |", "| --- | --- | --- | --- |"]
        for c in chals:
            link = f"/{route_of[c['slug']]}#{c['slug']}"
            has = "[writeup](%s)" % link if c["readme"] else "_pas de writeup_"
            lines.append(
                f"| `{c['name']}` | {c['value'] if c['value'] is not None else ''} | "
                f"{c['author']} | {has} |"
            )
        lines.append("")
    pages = [
        {
            "route": INDEX_ROUTE,
            "title": f"Writeups {ctf_name}",
            "content": "\n".join(lines),
            "menu": True,
        }
    ]
    for cat in cats:
        parts, _ = packed[cat]
        for i, part in enumerate(parts):
            ptitle = cat if len(parts) == 1 else f"{cat} ({i + 1}/{len(parts)})"
            body = [
                f"# Writeups — {ptitle}",
                "",
                f"[← Index des writeups](/{INDEX_ROUTE}) · {len(part['chals'])} challenges",
                "",
            ]
            for c in part["chals"]:
                body.append(_redacted_section(c))
            pages.append(
                {
                    "route": part["route"],
                    "title": f"Writeups — {ptitle}",
                    "content": "\n".join(body),
                    "menu": False,
                }
            )
    for p in pages:
        size = len(p["content"].encode())
        if size > MAX_PAGE_BYTES:
            raise SystemExit(
                f"page /{p['route']} : {size} octets > {MAX_PAGE_BYTES} (TEXT MariaDB = 64 Ko) ; "
                "scinder la catégorie"
            )
    return pages


def may_publish(end, now=None, force=False):
    """CTF ended (config `end` in the past), or --force."""
    if force:
        return True
    now = time.time() if now is None else now
    try:
        return bool(end) and int(end) <= now
    except (TypeError, ValueError):
        return False


# --- CTFd API -----------------------------------------------------------------


class Ctfd:
    def __init__(self, url, token):
        try:
            import requests
        except ImportError:
            sys.exit("pip install requests")
        self.url = url.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update(
            {"Authorization": f"Token {token}", "Content-Type": "application/json"}
        )

    def call(self, method, path, body=None):
        r = self.s.request(method, self.url + path, json=body, timeout=30)
        if r.status_code != 200:
            raise SystemExit(f"{method} {path} -> HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    def pages(self):
        return {p["route"]: p for p in self.call("GET", "/api/v1/pages")["data"]}

    def config(self, key):
        return self.call("GET", f"/api/v1/configs/{key}")["data"]["value"]


def upsert(api, pages, draft, existing=None):
    """Create or update every page. draft=True keeps them unreachable."""
    existing = api.pages() if existing is None else existing
    done = []
    for p in pages:
        body = {
            "title": p["title"],
            "content": p["content"],
            "draft": draft,
            "hidden": not (p["menu"] and not draft),
            "auth_required": False,
            "format": "markdown",
        }
        cur = existing.get(p["route"])
        if cur:
            api.call("PATCH", f"/api/v1/pages/{cur['id']}", body)
        else:
            api.call("POST", "/api/v1/pages", {**body, "route": p["route"]})
        done.append(p["route"])
    return done


def set_draft(api, pages, draft):
    existing = api.pages()
    missing = [p["route"] for p in pages if p["route"] not in existing]
    if missing:
        raise SystemExit(f"pages absentes (lancer --prepare d'abord) : {missing}")
    for p in pages:
        api.call(
            "PATCH",
            f"/api/v1/pages/{existing[p['route']]['id']}",
            {"draft": draft, "hidden": not (p["menu"] and not draft)},
        )


# --- static archive -------------------------------------------------------------

CSS = """body{font:16px/1.55 system-ui,sans-serif;margin:0;padding:2rem 1rem;max-width:52rem;margin-inline:auto}
:root{color-scheme:light dark}pre{overflow-x:auto;padding:.6rem .8rem;background:#8882;border-radius:6px}
code{font-size:.92em}table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{text-align:left;padding:.35rem .5rem;border-bottom:1px solid #8883}
img{max-width:100%}h1{font-size:1.5rem}h2{margin-top:2.2rem;border-top:1px solid #8884;padding-top:1rem}a{color:inherit}"""


def _static_name(route):
    return "index.html" if route == INDEX_ROUTE else route.split("/", 1)[1] + ".html"


def write_static(pages, out_dir):
    """Autonomous HTML (same cmarkgfm renderer as CTFd), links rewritten."""
    try:
        import cmarkgfm
        from cmarkgfm.cmark import Options
    except ImportError:
        sys.exit("pip install cmarkgfm (le rendu Markdown de CTFd)")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for p in pages:
        md = p["content"]
        for q in pages:
            md = md.replace(f"](/{q['route']})", f"]({_static_name(q['route'])})")
            md = md.replace(f"](/{q['route']}#", f"]({_static_name(q['route'])}#")
        body = cmarkgfm.markdown_to_html_with_extensions(
            md,
            extensions=["autolink", "table", "strikethrough"],
            options=Options.CMARK_OPT_UNSAFE,
        )
        page = (
            '<!doctype html>\n<html lang="fr">\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{html.escape(p['title'])}</title>\n<style>{CSS}</style>\n{body}\n"
            '<p><a href="../">Classement de cette édition</a></p>\n</html>\n'
        )
        (out / _static_name(p["route"])).write_text(page, encoding="utf-8")
    return [str(out / _static_name(p["route"])) for p in pages]


# --- main -----------------------------------------------------------------------


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--url", default=os.environ.get("CTFD_URL"))
    ap.add_argument("--token", default=os.environ.get("CTFD_TOKEN"))
    ap.add_argument("--challenges", default=str(CHALLENGES))
    ap.add_argument("--categories", help="ex: web,pwn (defaut : toutes)")
    ap.add_argument("--ctf-name", default=None)
    g = ap.add_mutually_exclusive_group()
    g.add_argument(
        "--prepare", action="store_true", help="cree/met a jour les pages en brouillon"
    )
    g.add_argument(
        "--publish",
        action="store_true",
        help="retire le brouillon (refuse avant `end`)",
    )
    g.add_argument("--unpublish", action="store_true", help="remet en brouillon")
    g.add_argument("--static", metavar="DIR", help="HTML autonome pour l'archive S3")
    g.add_argument(
        "--dump", metavar="DIR", help="ecrit le Markdown des pages (relecture)"
    )
    ap.add_argument(
        "--force", action="store_true", help="publier meme si `end` n'est pas passe"
    )
    a = ap.parse_args(argv)

    cats = set(a.categories.split(",")) if a.categories else None
    items = load_challenges(Path(a.challenges), cats)
    if not items:
        sys.exit("aucun challenge trouve")
    api = None
    if a.prepare or a.publish or a.unpublish:
        if not (a.url and a.token):
            sys.exit(
                "--url et --token (jeton API admin) requis ; ou CTFD_URL / CTFD_TOKEN"
            )
        api = Ctfd(a.url, a.token)
    name = a.ctf_name or (api.config("ctf_name") if api else None) or "NCTF26"
    pages = build_pages(items, ctf_name=name)
    with_readme = sum(1 for c in items if c["readme"])
    print(
        f"{len(items)} challenges, {with_readme} writeups, {len(pages)} pages "
        f"(max {max(len(p['content'].encode()) for p in pages)} octets)",
        flush=True,
    )

    if a.dump:
        Path(a.dump).mkdir(parents=True, exist_ok=True)
        for p in pages:
            Path(a.dump, p["route"].replace("/", "__") + ".md").write_text(p["content"])
        print(f"markdown ecrit dans {a.dump}")
    elif a.static:
        for f in write_static(pages, a.static):
            print("  " + f)
    elif a.prepare:
        upsert(api, pages, draft=True)
        print(
            f"{len(pages)} pages en brouillon (404 pour les joueurs) sur {api.url}/{INDEX_ROUTE}"
        )
    elif a.publish:
        end = api.config("end")
        if not may_publish(end, force=a.force):
            sys.exit(
                f"REFUS : `end` = {end or 'non defini'} n'est pas passe ; les writeups pendant "
                "l'epreuve, c'est la solution offerte. --force pour passer outre."
            )
        upsert(api, pages, draft=False)  # content refreshed AND published in one pass
        print(
            f"PUBLIE : {api.url}/{INDEX_ROUTE} (menu) + {len(pages) - 1} pages de categorie"
        )
    elif a.unpublish:
        set_draft(api, pages, True)
        print("remis en brouillon")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
