#!/usr/bin/env python3
"""
Working solver for model-inversion.

The oracle leaks a bilinear similarity between the probe and the memorised
record `r`:

    logit(P(SEALED|p)) = s(p) = (p/255)^T M (r/255) + C0          # M = E^T E

Recovery (closed form, white-box M):

  1. Invert the softmax to get the SEALED logit for any probe:
         s(p) = ln( P_SEALED / P_OTHER )
  2. Cancel the bias with a baseline probe p = 0:   s(0) = C0.
  3. Probe with p = 255 * e_i (attribute i set to 255, rest 0). Since (p/255)=e_i,
         s(255 e_i) - s(0) = e_i^T M (r/255) = (M (r/255))_i
     so D+1 queries give the whole vector  u = M (r/255).
  4. M is known white-box (M = E^T E from weights.npz) and positive definite, so
         r = 255 * M^{-1} u
     Round to the nearest byte and clip to 0..255. Recovery is exact.

The trap: u != r/255 because M is NOT diagonal. Reading the per-attribute
confidences off as the record (assuming the identity metric) yields garbage --
you must solve the linear system with M.

Usage:
    python3 solve.py                      # attack a local instance
    python3 solve.py http://HOST:8080     # attack a given instance
    python3 solve.py --offline            # self-contained offline proof (no server)
"""
import json
import math
import os
import sys
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(HERE, "..", "handout"), os.path.join(HERE, "..", "app"), HERE):
    sys.path.insert(0, p)

from model import Vault, D, S  # noqa: E402  (handout white-box scorer)


def sealed_logit(conf: dict) -> float:
    """Invert the two-class softmax: s = ln(P_SEALED / P_OTHER)."""
    return math.log(conf["SEALED"] / conf["OTHER"])


def recover(query_conf, M) -> np.ndarray:
    """Recover the record given a confidence oracle `query_conf(probe)->dict`
    and the white-box metric M."""
    base = sealed_logit(query_conf(np.zeros(D, dtype=int)))     # s(0) = C0
    u = np.zeros(D)
    for i in range(D):
        p = np.zeros(D, dtype=int)
        p[i] = 255
        u[i] = sealed_logit(query_conf(p)) - base               # (M (r/S))_i
    r = S * np.linalg.solve(M, u)                               # r = S M^{-1} u
    return np.clip(np.round(r), 0, 255).astype(int)


# --- live oracle over HTTP --------------------------------------------------
def _http_query(base_url):
    def q(probe):
        req = urllib.request.Request(
            f"{base_url}/query",
            data=json.dumps({"probe": [int(v) for v in probe]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["confidence"]
    return q


def _fetch_weights(base_url):
    dst = os.path.join(HERE, "weights.npz")
    with urllib.request.urlopen(f"{base_url}/assets/weights.npz", timeout=30) as r:
        open(dst, "wb").write(r.read())
    return dst


def solve_live(base_url):
    wpath = None
    for c in ("weights.npz", "../handout/weights.npz", "../app/weights.npz"):
        cand = os.path.join(HERE, c)
        if os.path.exists(cand):
            wpath = cand
            break
    if wpath is None:
        wpath = _fetch_weights(base_url)
    M = Vault(wpath).M

    rec = recover(_http_query(base_url), M)
    print("[+] recovered record:", rec.tolist())

    req = urllib.request.Request(
        f"{base_url}/submit",
        data=json.dumps({"record": rec.tolist()}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        print("[*] server:", r.read().decode())


# --- offline soundness proof (no server) ------------------------------------
def solve_offline():
    """Simulate the exact server logic locally and confirm the attack recovers
    an arbitrary memorised record. Also confirms the identity-metric trap fails."""
    import hashlib
    import hmac

    wpath = os.path.join(HERE, "..", "app", "weights.npz")
    if not os.path.exists(wpath):
        wpath = os.path.join(HERE, "..", "handout", "weights.npz")
    vault = Vault(wpath)

    # derive a per-team record exactly as the server does
    def derive_record(secret):
        out = bytearray()
        i = 0
        while len(out) < D:
            out.extend(hmac.new(secret.encode(),
                                b"model-inversion-record|%d" % i,
                                hashlib.sha256).digest())
            i += 1
        return np.frombuffer(bytes(out[:D]), dtype=np.uint8).astype(int)

    ok = True
    for team in ("alpha", "bravo", "charlie"):
        secret = hmac.new(team.encode(), b"ml-model-inversion", hashlib.sha256).hexdigest()
        r_true = derive_record(secret)
        q = lambda p, r=r_true: vault.confidence(p, r)      # the live oracle
        r_hat = recover(q, vault.M)
        linf = int(np.max(np.abs(r_hat - r_true)))
        # trap: naive identity-metric read of the same probes
        base = sealed_logit(q(np.zeros(D, dtype=int)))
        u = np.array([sealed_logit(q(np.eye(D, dtype=int)[i] * 255)) - base for i in range(D)])
        naive = np.clip(np.round(S * u), 0, 255).astype(int)
        naive_linf = int(np.max(np.abs(naive - r_true)))
        print(f"team {team:8s}: recovered L-inf={linf} (<=2 unlocks) | "
              f"identity-metric trap L-inf={naive_linf}")
        ok = ok and (linf <= 2) and (naive_linf > 2)
    print("[offline] all teams recovered exactly, trap fails:", ok)
    return ok


def main():
    if "--offline" in sys.argv:
        sys.exit(0 if solve_offline() else 1)
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")
    solve_live(base)


if __name__ == "__main__":
    main()
