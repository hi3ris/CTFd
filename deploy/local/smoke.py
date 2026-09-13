#!/usr/bin/env python3
"""Verifie, sur un CTFd en marche, ce qu'un participant verra : theme hibris,
aucune trace CTFd, assets, pages d'erreur, API, plugins.

  python3 deploy/local/smoke.py [--url http://localhost:8000] [--expect-challenges 36]

Sort en erreur au premier lot de verifications ratees (toutes sont listees).
"""
import argparse
import os
import re
import sys

import requests

ADMIN = ("admin", "admin")
fails = []


def check(name, cond, detail=""):
    print(("  [ok]   " if cond else "  [fail] ") + name + (f"  -- {detail}" if detail and not cond else ""), flush=True)
    if not cond:
        fails.append(name)


def nonce_of(html):
    m = re.search(r"'csrfNonce':\s*\"([0-9a-f]+)\"", html)
    return m.group(1) if m else None


def login(url, name, password):
    s = requests.Session()
    r = s.get(url + "/login")
    s.post(url + "/login", data={"name": name, "password": password, "nonce": nonce_of(r.text)})
    s.headers["CSRF-Token"] = nonce_of(s.get(url + "/").text) or ""
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("CTFD_URL", "http://localhost:8000"))
    ap.add_argument("--expect-challenges", type=int, default=36)
    a = ap.parse_args()
    url = a.url.rstrip("/")
    anon = requests.Session()

    print("== pages publiques ==")
    pages = {"/": 200, "/login": 200, "/register": 200, "/scoreboard": 200, "/users": 200, "/teams": 200,
             "/nope-404": 404, "/challenges": 302}
    body = {}
    for p, want in pages.items():
        r = anon.get(url + p, allow_redirects=False)
        body[p] = r.text
        check(f"GET {p} -> {want}", r.status_code == want, f"got {r.status_code}")

    print("== theme hibris ==")
    home = body["/"]
    check("police Tourney chargee (theme hibris actif)", "family=Tourney" in home)
    check("meta theme-color", 'name="theme-color" content="#00040d"' in home)
    check("footer : Organise par CERT.tg + logo", "Organisé par CERT.tg" in home and "img/cert.png" in home)
    check("footer : Powered by Hibris -> ramses.dagban.tg", "Powered by <strong>Hibris</strong>" in home and "https://ramses.dagban.tg/" in home)
    check("accueil : hero NCTF25 en place (CMS remplace)", 'class="nctf-hero"' in home)
    check("aucune trace 'ctfd.io' sur l'accueil", "ctfd.io" not in home.lower())
    check("aucune trace 'Powered by CTFd'", "Powered by CTFd" not in home)
    e404 = body["/nope-404"]
    check("404 : fenetre terminal NCTF", 'class="term-window"' in e404 and "ressource introuvable" in e404)
    check("404 : plus de 'File not found'", "File not found" not in e404)

    print("== assets references par les pages ==")
    seen = set()
    for p in ("/", "/login", "/scoreboard"):
        for u in re.findall(r'(?:href|src)="(/themes/[^"]+)"', body[p]):
            k = u.split("?")[0]
            if k in seen:
                continue
            seen.add(k)
            r = anon.get(url + u)
            check(f"{r.status_code} {k}", r.status_code == 200)
    for u in ("/plugins/team_instancer/assets/view.js", "/plugins/team_instancer/assets/view.html"):
        check(f"plugin asset {u}", anon.get(url + u).status_code == 200)

    print("== admin / API ==")
    adm = login(url, *ADMIN)
    r = adm.get(url + "/api/v1/configs/ctf_theme")
    check("ctf_theme == hibris", r.ok and r.json()["data"]["value"] == "hibris", r.text[:120])
    r = adm.get(url + "/api/v1/configs/user_mode")
    check("user_mode == teams", r.ok and r.json()["data"]["value"] == "teams")
    r = adm.get(url + "/api/v1/challenges?view=admin")
    chals = r.json()["data"] if r.ok else []
    check(f"{a.expect_challenges} challenges importes", len(chals) == a.expect_challenges, f"got {len(chals)}")
    types = {c["type"] for c in chals}
    check("types presents : team_instance + dynamic", {"team_instance", "dynamic"} <= types, str(types))
    by_cat = {}
    for c in chals:
        by_cat[c["category"]] = by_cat.get(c["category"], 0) + 1
    print("   par categorie : " + ", ".join(f"{k}={v}" for k, v in sorted(by_cat.items())))
    r = adm.get(url + "/api/v1/challenges/types")
    check("type team_instance enregistre cote serveur", r.ok and "team_instance" in r.json()["data"])
    ids = {c["name"]: c["id"] for c in chals}

    print("== joueur ==")
    ply = login(url, "playtest", "playtest")
    r = ply.get(url + "/challenges")
    check("joueur : /challenges 200", r.status_code == 200, f"got {r.status_code}")

    # Chaine IA, testee par le comportement (l'API n'expose pas `requirements`) :
    # ai1/ai2/ai3 invisibles tant que ai0 n'est pas resolu ; ai1 apparait des
    # que ai0 l'est, ai2/ai3 restent caches. Idempotent : si ai0 est deja resolu
    # par l'equipe de test (playtest precedent), on verifie seulement l'etat final.
    def ai_visible():
        r = ply.get(url + "/api/v1/challenges")
        return {c["name"] for c in (r.json()["data"] if r.ok else []) if c["category"] == "ai"}

    seen = ai_visible()
    solved = {s["challenge_id"] for s in ply.get(url + "/api/v1/teams/me/solves").json().get("data", [])}
    if "ai0-leaked-transcript" in ids and ids["ai0-leaked-transcript"] not in solved:
        check("chaine IA : ai1/ai2/ai3 masques avant ai0", not ({"ai1-naive-guard", "ai2-output-filter", "ai3-tool-abuse"} & seen), str(sorted(seen)))
        yml = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "challenges", "ai", "ai0-leaked-transcript", "challenge.yml")
        m = re.search(r"^\s*-\s*(NCTF\{[^}]+\})", open(yml).read(), re.M)
        if m:
            r = ply.post(url + "/api/v1/challenges/attempt", json={"challenge_id": ids["ai0-leaked-transcript"], "submission": m.group(1)})
            st = r.json().get("data", {}).get("status") if r.ok else f"http {r.status_code}"
            check("chaine IA : flag statique de ai0 accepte (team playtest)", st in ("correct", "already_solved"), str(st))
            seen = ai_visible()
    check("chaine IA : ai1 visible une fois ai0 resolu", "ai1-naive-guard" in seen, str(sorted(seen)))
    check("chaine IA : ai2/ai3 toujours masques (ai1 non resolu)", not ({"ai2-output-filter", "ai3-tool-abuse"} & seen), str(sorted(seen)))

    print()
    if fails:
        print(f"RESULTAT : {len(fails)} verification(s) en echec\n  - " + "\n  - ".join(fails)); sys.exit(1)
    print("RESULTAT : tout passe")


if __name__ == "__main__":
    main()
