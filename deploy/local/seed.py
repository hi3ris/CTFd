#!/usr/bin/env python3
"""Initialise un CTFd vierge comme il le sera le jour J, puis importe les
challenges. Idempotent : relancable sans casser ce qui existe.

  python3 deploy/local/seed.py [--url http://localhost:8000] [--only web/jwt-cousin ...]

Etapes :
  1. attend que CTFd reponde ;
  2. /setup  : nom, mode EQUIPES, admin, theme hibris ;
  3. accueil : remplace le contenu CMS par defaut (qui trahit CTFd) par
     deploy/theme-home-hero.html ;
  4. jeton API admin -> ctfcli -> `ctf challenge install` sur chaque dossier,
     dans un ordre qui respecte les prerequis (ai0 -> ai1 -> ai2 -> ai3) ;
  5. une equipe de test (playtest / playtest) pour le playtest et les essais
     manuels.

Pre-requis sur la machine : pip install ctfcli requests
Identifiants crees : admin / admin (compte admin), playtest / playtest (joueur).
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("pip install requests ctfcli")

ROOT = Path(__file__).resolve().parents[2]
CHALLENGES = ROOT / "challenges"
HERO = ROOT / "deploy" / "theme-home-hero.html"

ADMIN = {"name": "admin", "email": "admin@nctf.local", "password": "admin"}
PLAYER = {"name": "playtest", "email": "playtest@nctf.local", "password": "playtest"}
TEAM = {"name": "playtest", "password": "playtest"}

# Les prerequis sont resolus PAR NOM par ctfcli : la cible doit deja exister.
INSTALL_LAST = ["ai/ai0-leaked-transcript", "ai/ai1-naive-guard", "ai/ai2-output-filter", "ai/ai3-tool-abuse"]


def log(msg):
    print(msg, flush=True)


def nonce_of(html):
    m = re.search(r"'csrfNonce':\s*\"([0-9a-f]+)\"", html) or re.search(r'name="nonce" value="([0-9a-f]+)"', html)
    if not m:
        raise SystemExit("nonce CSRF introuvable dans la page")
    return m.group(1)


def wait_for(url, timeout=180):
    log(f">> attente de {url}")
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = requests.get(url + "/healthcheck", timeout=5)
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise SystemExit("CTFd ne repond pas (make local-logs ?)")


def do_setup(url):
    s = requests.Session()
    r = s.get(url + "/setup", allow_redirects=False)
    if r.status_code != 200:
        log("   setup deja fait, on passe")
        return
    data = {
        "ctf_name": "NCTF25", "ctf_description": "National CTF - CERT.tg",
        "user_mode": "teams", "name": ADMIN["name"], "email": ADMIN["email"], "password": ADMIN["password"],
        "ctf_theme": "hibris", "theme_color": "", "verify_emails": "false",
        "challenge_visibility": "private", "account_visibility": "public", "score_visibility": "public",
        "registration_visibility": "public", "start": "", "end": "", "team_size": "",
        "nonce": nonce_of(r.text),
    }
    r = s.post(url + "/setup", data=data, allow_redirects=False)
    if r.status_code not in (302, 200):
        raise SystemExit(f"setup: HTTP {r.status_code}\n{r.text[:500]}")
    log("   setup OK : NCTF25, mode equipes, theme hibris, admin/admin")


def admin_session(url):
    s = requests.Session()
    r = s.get(url + "/login")
    r = s.post(url + "/login", data={"name": ADMIN["name"], "password": ADMIN["password"], "nonce": nonce_of(r.text)}, allow_redirects=False)
    if r.status_code != 302:
        raise SystemExit("login admin impossible")
    s.headers["CSRF-Token"] = nonce_of(s.get(url + "/").text)
    return s


def api_token(s, url):
    r = s.post(url + "/api/v1/tokens", json={"description": "seed local"})
    r.raise_for_status()
    return r.json()["data"]["value"]


def set_home(s, url):
    if not HERO.exists():
        log(f"   {HERO} absent, accueil laisse tel quel"); return
    pages = s.get(url + "/api/v1/pages").json()["data"]
    home = next((p for p in pages if p["route"] in ("index", "")), None)
    if not home:
        log("   page d'accueil introuvable"); return
    content = HERO.read_text(encoding="utf-8")
    r = s.patch(url + f"/api/v1/pages/{home['id']}", json={"content": content, "format": "html"})
    r.raise_for_status()
    log("   accueil remplace par deploy/theme-home-hero.html")


def set_configs(s, url):
    r = s.patch(url + "/api/v1/configs", json={"ctf_theme": "hibris", "user_mode": "teams"})
    r.raise_for_status()


def installed_names(s, url):
    return {c["name"] for c in s.get(url + "/api/v1/challenges?view=admin").json()["data"]}


def install_challenges(url, token, only, already):
    dirs = sorted(str(Path(p).parent.relative_to(CHALLENGES)) for p in glob.glob(str(CHALLENGES / "*/*/challenge.yml")))
    if only:
        dirs = [d for d in dirs if d in only]
    ordered = [d for d in dirs if d not in INSTALL_LAST] + [d for d in INSTALL_LAST if d in dirs]
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / ".ctf").mkdir()
        (Path(tmp) / ".ctf" / "config").write_text(f"[config]\nurl = {url}\naccess_token = {token}\n\n[challenges]\n")
        ok, ko, skip = [], [], []
        for d in ordered:
            name = re.search(r"^name:\s*(.+)$", (CHALLENGES / d / "challenge.yml").read_text(), re.M).group(1).strip().strip('"')
            if name in already:
                skip.append(d); continue
            log(f">> ctf challenge install {d}")
            p = subprocess.run(["ctf", "challenge", "install", str(CHALLENGES / d)], cwd=tmp, capture_output=True, text=True)
            if p.returncode == 0:
                ok.append(d)
            else:
                ko.append(d); log("   ECHEC\n" + "\n".join("   | " + l for l in (p.stdout + p.stderr).strip().splitlines()[-12:]))
    return ok, ko, skip


def ensure_player(s, url):
    users = {u["name"]: u for u in s.get(url + "/api/v1/users?view=admin").json()["data"]}
    if PLAYER["name"] not in users:
        r = s.post(url + "/api/v1/users", json={**PLAYER, "type": "user", "verified": True})
        r.raise_for_status(); users[PLAYER["name"]] = r.json()["data"]
    teams = {t["name"]: t for t in s.get(url + "/api/v1/teams?view=admin").json()["data"]}
    if TEAM["name"] not in teams:
        r = s.post(url + "/api/v1/teams", json=TEAM)
        r.raise_for_status(); teams[TEAM["name"]] = r.json()["data"]
    team = teams[TEAM["name"]]
    members = s.get(url + f"/api/v1/teams/{team['id']}/members").json()["data"]
    if users[PLAYER["name"]]["id"] not in members:
        s.post(url + f"/api/v1/teams/{team['id']}/members", json={"user_id": users[PLAYER["name"]]["id"]}).raise_for_status()
    log(f"   joueur {PLAYER['name']}/{PLAYER['password']} dans l'equipe {TEAM['name']} (id {team['id']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("CTFD_URL", "http://localhost:8000"))
    ap.add_argument("--only", nargs="*", default=[], help="ex: web/jwt-cousin misc/proto-fuzz")
    ap.add_argument("--no-challenges", action="store_true")
    a = ap.parse_args()
    url = a.url.rstrip("/")

    wait_for(url)
    log(">> setup"); do_setup(url)
    s = admin_session(url)
    log(">> config"); set_configs(s, url); set_home(s, url)
    log(">> equipe de test"); ensure_player(s, url)
    if a.no_challenges:
        return
    log(">> challenges")
    ok, ko, skip = install_challenges(url, api_token(s, url), set(a.only), installed_names(s, url))
    total = len(installed_names(s, url))
    log(f"\ninstalles : {len(ok)}   deja presents : {len(skip)}   en echec : {len(ko)}   -> {total} challenges sur la plateforme")
    if ko:
        log("EN ECHEC : " + ", ".join(ko)); sys.exit(1)


if __name__ == "__main__":
    main()
