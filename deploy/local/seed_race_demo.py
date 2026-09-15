#!/usr/bin/env python3
"""Peuple le scoreboard de fausses écuries pour VOIR la course bouger en local.

Sans ça, l'installation locale n'a qu'une équipe (playtest) -> une seule voiture,
rien à dépasser. Ici on crée N écuries et on leur attribue des points via des
*awards* (bonus admin) — aucun challenge à résoudre, aucun impact sur le vrai
scoring. En mode --live, on rebump les scores en boucle : les voitures se
dépassent, le nitro se déclenche, exactement comme le jour J.

  python3 deploy/local/seed_race_demo.py                 # crée 12 écuries + scores
  python3 deploy/local/seed_race_demo.py --teams 16
  python3 deploy/local/seed_race_demo.py --live          # + rebump en boucle (Ctrl-C)
  python3 deploy/local/seed_race_demo.py --countdown 30  # départ dans 30s (teste le compte à rebours)
  python3 deploy/local/seed_race_demo.py --clear         # retire les écuries de démo

Identifiants admin : admin / admin (créés par `make local-seed`).
Les écuries de démo sont préfixées « GP· » et nettoyables avec --clear ou `make local-reset`.
"""
import argparse
import os
import random
import re
import sys
import time

import requests

PREFIX = "GP·"  # "GP·" — repère les équipes de démo
NAMES = [
    "Zébu Turbo",
    "Baobab Racing",
    "Kékéli Motors",
    "Akwaba Speed",
    "Mono Velocity",
    "Kara Drift",
    "Lomé Lightning",
    "Sokodé Sprint",
    "Atakpamé RX",
    "Kpalimé Boost",
    "Fazao Flash",
    "Togoville GT",
    "Aného Arrow",
    "Dapaong Dash",
    "Bassar Bolt",
    "Vogan Vortex",
    "Tsévié Torque",
    "Notsé Nitro",
    "Badou Blaze",
    "Kpémé Comet",
]


def nonce_of(html):
    m = re.search(r"'csrfNonce':\s*\"([0-9a-f]+)\"", html) or re.search(
        r'name="nonce" value="([0-9a-f]+)"', html
    )
    return m.group(1) if m else ""


def admin(url):
    s = requests.Session()
    r = s.get(url + "/login")
    r = s.post(
        url + "/login",
        data={"name": "admin", "password": "admin", "nonce": nonce_of(r.text)},
        allow_redirects=False,
    )
    if r.status_code != 302:
        sys.exit("login admin impossible (make local-seed d'abord ?)")
    s.headers["CSRF-Token"] = nonce_of(s.get(url + "/").text)
    return s


def teams_index(s, url):
    return {
        t["name"]: t for t in s.get(url + "/api/v1/teams?view=admin").json()["data"]
    }


def users_index(s, url):
    return {
        u["name"]: u for u in s.get(url + "/api/v1/users?view=admin").json()["data"]
    }


def ensure_fleet(s, url, n):
    """Crée n écuries (équipe + capitaine) si absentes ; renvoie [(team_id, user_id, name)]."""
    teams = teams_index(s, url)
    users = users_index(s, url)
    fleet = []
    for i in range(n):
        label = NAMES[i % len(NAMES)] + (
            f" {i//len(NAMES)+1}" if i >= len(NAMES) else ""
        )
        tname = PREFIX + label
        uname = "gp_racer_%02d" % (i + 1)
        team = teams.get(tname)
        if not team:
            r = s.post(url + "/api/v1/teams", json={"name": tname, "password": "demo"})
            if not r.ok:
                print("  team KO", tname, r.status_code, r.text[:120])
                continue
            team = r.json()["data"]
            teams[tname] = team
        user = users.get(uname)
        if not user:
            r = s.post(
                url + "/api/v1/users",
                json={
                    "name": uname,
                    "email": uname + "@gp.local",
                    "password": "demo",
                    "type": "user",
                    "verified": True,
                },
            )
            if not r.ok:
                print("  user KO", uname, r.status_code, r.text[:120])
                continue
            user = r.json()["data"]
            users[uname] = user
        members = (
            s.get(url + f"/api/v1/teams/{team['id']}/members").json().get("data", [])
        )
        if user["id"] not in members:
            s.post(
                url + f"/api/v1/teams/{team['id']}/members",
                json={"user_id": user["id"]},
            )
        fleet.append((team["id"], user["id"], tname))
    return fleet


def award(s, url, user_id, value):
    return s.post(
        url + "/api/v1/awards",
        json={
            "user_id": user_id,
            "value": int(value),
            "name": "Grand Prix",
            "category": "demo",
        },
    )


def clear(s, url):
    # supprime les écuries de démo (cascade -> membres + awards)
    n = 0
    for name, t in teams_index(s, url).items():
        if name.startswith(PREFIX):
            s.delete(url + f"/api/v1/teams/{t['id']}")
            n += 1
    for name, u in users_index(s, url).items():
        if name.startswith("gp_racer_"):
            s.delete(url + f"/api/v1/users/{u['id']}")
    print(f"  {n} écuries de démo retirées.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--url",
        default=os.environ.get(
            "CTFD_URL", "http://localhost:" + os.environ.get("CTFD_PORT", "8000")
        ),
    )
    ap.add_argument("--teams", type=int, default=12)
    ap.add_argument(
        "--live",
        action="store_true",
        help="rebump les scores en boucle (Ctrl-C pour arrêter)",
    )
    ap.add_argument(
        "--interval",
        type=float,
        default=6.0,
        help="secondes entre deux rebumps (--live)",
    )
    ap.add_argument(
        "--countdown",
        type=int,
        default=0,
        help="règle start = maintenant + N secondes (teste le départ)",
    )
    ap.add_argument("--clear", action="store_true")
    a = ap.parse_args()
    url = a.url.rstrip("/")
    s = admin(url)

    if a.clear:
        clear(s, url)
        return

    if a.countdown:
        now = int(time.time())
        s.patch(
            url + "/api/v1/configs",
            json={
                "start": str(now + a.countdown),
                "end": str(now + a.countdown + 3600),
            },
        )
        print(
            f"  départ dans {a.countdown}s, fin +1h (compte à rebours visible sur /scoreboard)."
        )

    fleet = ensure_fleet(s, url, a.teams)
    print(f"  {len(fleet)} écuries prêtes.")
    # score initial étalé pour un peloton crédible
    for i, (_tid, uid, _n) in enumerate(fleet):
        award(s, url, uid, random.randint(50, 100) * (len(fleet) - i))
    print("  scores initiaux attribués. Ouvre /scoreboard 🏁")

    if not a.live:
        return
    print("  --live : rebump en boucle (Ctrl-C pour arrêter)…")
    try:
        while True:
            time.sleep(a.interval)
            for (_tid, uid, name) in random.sample(fleet, k=max(1, len(fleet) // 3)):
                pts = random.choice([100, 150, 200, 250, 300, 500])
                award(s, url, uid, pts)
            print("  +points distribués", flush=True)
    except KeyboardInterrupt:
        print("\n  arrêt. (--clear pour retirer les écuries de démo)")


if __name__ == "__main__":
    main()
