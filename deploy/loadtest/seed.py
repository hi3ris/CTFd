#!/usr/bin/env python3
"""Comptes et cibles du test de charge -- jamais sur la base reelle de l'epreuve.

  python3 deploy/loadtest/seed.py --teams 300 [--url http://localhost:8000]
  python3 deploy/loadtest/seed.py --purge

Cree N equipes `lt-0001`..`lt-0300` (un joueur chacune, mot de passe commun tire
au hasard) et ecrit deploy/loadtest/out/accounts.json, que lisent scenarios.js et
instancer.js :

  {"url": ..., "password": ..., "teams": [{"team": "lt-0001", "user": "lt-0001"}],
   "flags": [{"challenge_id": 12, "flag": "NCTF{...}"}],   # flags statiques connus
   "instance_challenges": [4, 9, ...]}                       # type team_instance

Les flags viennent des `challenge.yml` du depot (entrees `flags:` en chaine) croises
avec les challenges presents sur la plateforme : ce sont les memes challenges que
`make local-seed` / ctfcli installent, donc les memes flags.

Authentification (comme preflight.py) : CTFD_TOKEN (jeton API admin), sinon
CTFD_ADMIN_USER / CTFD_ADMIN_PASS, sinon admin/admin (stack locale).

Garde-fous :
  * refuse toute URL non locale sans --allow-remote ;
  * meme avec --allow-remote, refuse si la plateforme porte deja plus de
    --max-real-teams equipes hors `lt-` (c'est alors l'epreuve, pas la repetition) ;
  * refuse si `start` est dans le futur : /attempt et /spawn repondent 403 hors
    fenetre, le test ne mesurerait rien -- lancer le test AVANT de poser les
    fenetres de l'epreuve (RUNBOOK §2).

`--purge` supprime les equipes et joueurs `lt-*` (leurs solves partent avec eux)
puis force le recalcul de la valeur des challenges dynamiques, que les solves de
charge avaient fait decroitre. Les first bloods pris par la charge sont rejoues
au prochain vrai premier solve (le plugin compare les ids de solve). Restaurer le
dump pris avant le test reste la voie propre (RUNBOOK §2).
"""
import argparse
import glob
import json
import os
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    import yaml
except ImportError:
    sys.exit("pip install requests pyyaml")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deploy" / "local"))
from seed import nonce_of, wait_for  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
PREFIX = "lt-"
FLAG_RE = re.compile(r"NCTF\{[^}]+\}")

__all__ = ["nonce_of"]


def log(msg):
    print(msg, flush=True)


# --- pure helpers (tested) -------------------------------------------------


def team_name(i):
    return f"{PREFIX}{i:04d}"


def is_loadtest_name(name):
    return bool(re.fullmatch(re.escape(PREFIX) + r"\d{4}", name or ""))


def static_flags(challenge_dirs):
    """{challenge name: first static flag} from challenge.yml files.
    Only string entries count (team_hmac flags are per team)."""
    out = {}
    for d in challenge_dirs:
        try:
            y = yaml.safe_load(Path(d, "challenge.yml").read_text()) or {}
        except (OSError, yaml.YAMLError):
            continue
        for fl in y.get("flags") or []:
            if isinstance(fl, str) and FLAG_RE.fullmatch(fl.strip()):
                out[y.get("name")] = fl.strip()
                break
    return out


def targets(platform_challenges, flags_by_name):
    """Split the platform's challenge list into (static flag targets, instance ids)."""
    flags, instances = [], []
    for c in platform_challenges:
        if c.get("state", "visible") != "visible":
            continue
        if c.get("type") == "team_instance":
            instances.append(c["id"])
        f = flags_by_name.get(c["name"])
        if f and c.get("type") != "team_instance":
            flags.append({"challenge_id": c["id"], "flag": f, "name": c["name"]})
    return flags, instances


def guard(url, real_teams, start, now, allow_remote, max_real_teams):
    """Return a refusal message or None."""
    host = urlparse(url).hostname or ""
    if host not in ("localhost", "127.0.0.1", "::1") and not allow_remote:
        return f"{url} n'est pas la stack locale : ajouter --allow-remote (front de repetition seulement)"
    if real_teams > max_real_teams:
        return (
            f"{real_teams} equipes hors '{PREFIX}' sur la plateforme (> {max_real_teams}) : "
            "c'est l'epreuve, pas la repetition. Refus."
        )
    if start and int(start) > now:
        return "`start` est dans le futur : /attempt et /spawn repondraient 403. Lancer le test avant de poser les fenetres."
    return None


def paginate(fetch, what):
    """Follow meta.pagination.next of a CTFd list endpoint (50 per page)."""
    out, page = [], 1
    while page:
        body = fetch(f"/api/v1/{what}?view=admin&page={page}")
        out.extend(body["data"])
        page = (body.get("meta") or {}).get("pagination", {}).get("next")
    return out


# --- platform ---------------------------------------------------------------


def admin_session(url):
    """Token first (CTFD_TOKEN), else a password login (CTFD_ADMIN_USER/PASS,
    default admin/admin for the local stack)."""
    s = requests.Session()
    token = os.environ.get("CTFD_TOKEN")
    if token:
        # CTFd only honours the token when the request is application/json.
        s.headers["Authorization"] = f"Token {token}"
        s.headers["Content-Type"] = "application/json"
        r = s.get(url + "/api/v1/users/me")
        if r.status_code != 200:
            sys.exit("CTFD_TOKEN refuse (jeton API admin : Settings > Access Tokens)")
        return s
    user = os.environ.get("CTFD_ADMIN_USER", "admin")
    password = os.environ.get("CTFD_ADMIN_PASS", "admin")
    r = s.get(url + "/login")
    r = s.post(
        url + "/login",
        data={"name": user, "password": password, "nonce": nonce_of(r.text)},
        allow_redirects=False,
    )
    if r.status_code != 302:
        sys.exit(
            "login admin impossible : CTFD_TOKEN, ou CTFD_ADMIN_USER / CTFD_ADMIN_PASS"
        )
    s.headers["CSRF-Token"] = nonce_of(s.get(url + "/").text)
    return s


def list_all(s, url, what):
    if what == "challenges":  # not paginated
        return s.get(url + "/api/v1/challenges?view=admin").json()["data"]
    return paginate(lambda path: s.get(url + path).json(), what)


def create_accounts(s, url, n, password):
    users = {u["name"]: u for u in list_all(s, url, "users")}
    teams = {t["name"]: t for t in list_all(s, url, "teams")}
    made = 0
    for i in range(1, n + 1):
        name = team_name(i)
        if name not in users:
            r = s.post(
                url + "/api/v1/users",
                json={
                    "name": name,
                    "email": f"{name}@loadtest.invalid",
                    "password": password,
                    "type": "user",
                    "verified": True,
                },
            )
            r.raise_for_status()
            users[name] = r.json()["data"]
        if name not in teams:
            r = s.post(url + "/api/v1/teams", json={"name": name, "password": password})
            r.raise_for_status()
            teams[name] = r.json()["data"]
            made += 1
        tid = teams[name]["id"]
        members = s.get(url + f"/api/v1/teams/{tid}/members").json()["data"]
        if users[name]["id"] not in members:
            s.post(
                url + f"/api/v1/teams/{tid}/members",
                json={"user_id": users[name]["id"]},
            ).raise_for_status()
        if i % 50 == 0:
            log(f"   {i}/{n} equipes")
    return made


def purge(s, url):
    n = 0
    for t in list_all(s, url, "teams"):
        if is_loadtest_name(t["name"]):
            s.delete(url + f"/api/v1/teams/{t['id']}", json={}).raise_for_status()
            n += 1
    for u in list_all(s, url, "users"):
        if is_loadtest_name(u["name"]):
            s.delete(url + f"/api/v1/users/{u['id']}", json={}).raise_for_status()
    # Dynamic values decayed with the loadtest solves: an empty PATCH makes
    # CTFd recompute them from the solves that remain.
    fixed = 0
    for c in list_all(s, url, "challenges"):
        if c.get("type") == "dynamic":
            s.patch(url + f"/api/v1/challenges/{c['id']}", json={}).raise_for_status()
            fixed += 1
    return n, fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--url",
        default=os.environ.get(
            "CTFD_URL", "http://localhost:" + os.environ.get("CTFD_PORT", "8000")
        ),
    )
    ap.add_argument("--teams", type=int, default=300)
    ap.add_argument("--purge", action="store_true")
    ap.add_argument("--allow-remote", action="store_true")
    ap.add_argument("--max-real-teams", type=int, default=20)
    ap.add_argument("--out", default=str(OUT / "accounts.json"))
    a = ap.parse_args()
    url = a.url.rstrip("/")

    wait_for(url, timeout=60)
    s = admin_session(url)
    teams = list_all(s, url, "teams")
    real = sum(1 for t in teams if not is_loadtest_name(t["name"]))
    start = s.get(url + "/api/v1/configs/start").json()["data"]["value"]
    import time

    msg = guard(url, real, start, int(time.time()), a.allow_remote, a.max_real_teams)
    if msg:
        sys.exit("REFUS : " + msg)

    if a.purge:
        n, fixed = purge(s, url)
        log(
            f"purge : {n} equipe(s) de charge supprimee(s), {fixed} valeurs dynamiques recalculees"
        )
        return

    password = secrets.token_urlsafe(12)
    log(f">> {a.teams} equipes de charge sur {url}")
    made = create_accounts(s, url, a.teams, password)
    chals = list_all(s, url, "challenges")
    flags, instances = targets(
        chals, static_flags(glob.glob(str(ROOT / "challenges" / "*" / "*")))
    )
    if not flags:
        sys.exit(
            "aucun flag statique connu sur la plateforme : lancer make local-seed d'abord"
        )
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(
        json.dumps(
            {
                "url": url,
                "password": password,
                "teams": [
                    {"team": team_name(i), "user": team_name(i)}
                    for i in range(1, a.teams + 1)
                ],
                "flags": flags,
                "instance_challenges": instances,
            },
            indent=1,
        )
    )
    os.chmod(a.out, 0o600)
    log(
        f"   {made} nouvelle(s) equipe(s) ; {len(flags)} flags statiques, {len(instances)} challenges "
        f"a instance -> {a.out}"
    )


if __name__ == "__main__":
    main()
