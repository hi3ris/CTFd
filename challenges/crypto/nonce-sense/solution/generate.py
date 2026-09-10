#!/usr/bin/env python3
"""
AUTHOR-ONLY generator for the 'nonce-sense' challenge.

Produces the public artifact ../capture.json and prints the flag.
This file is NOT distributed to players (it reveals the private key).

Design
------
* Curve: secp256k1 (real, standard curve, order q ~ 2^256).
* The signing device has a broken RNG: every ECDSA nonce k has its most
  significant byte forced to zero, i.e. 0 < k < 2**248.  That is an 8-bit
  bias -> the Hidden Number Problem (HNP) is solvable by lattice reduction
  from a few dozen signatures.
* We emit 60 such biased signatures.
* DECOY: two extra signatures share an identical r value.  They are produced
  with nonces k and (q - k).  x(kG) == x((q-k)G), so r is identical, yet the
  nonces are NOT equal -> the classic "reused nonce" two-signature key
  recovery gives a WRONG private key (refutable in seconds against the public
  key).  Those two nonces are full-range (not top-byte-zero), so they must be
  excluded from the HNP lattice.
* The public key Q = d*G is published so any candidate key is trivially
  checkable; the flag is derived deterministically from the true key.
"""
import hashlib, json, os, secrets, sys

# ---- secp256k1 ------------------------------------------------------------
P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
A  = 0
B  = 7
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
Q_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (Gx, Gy)

def inv(x, m): return pow(x % m, -1, m)

def ec_add(Pt, Qt):
    if Pt is None: return Qt
    if Qt is None: return Pt
    x1, y1 = Pt; x2, y2 = Qt
    if x1 == x2 and (y1 + y2) % P == 0: return None
    if Pt == Qt:
        lam = (3 * x1 * x1 + A) * inv(2 * y1, P) % P
    else:
        lam = (y2 - y1) * inv(x2 - x1, P) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)

def ec_mul(k, Pt):
    R = None
    k %= Q_ORDER
    while k:
        if k & 1: R = ec_add(R, Pt)
        Pt = ec_add(Pt, Pt)
        k >>= 1
    return R

def h_of(msg: str) -> int:
    return int.from_bytes(hashlib.sha256(msg.encode()).digest(), "big") % Q_ORDER

def sign(d, msg, k):
    z = h_of(msg)
    R = ec_mul(k, G)
    r = R[0] % Q_ORDER
    s = inv(k, Q_ORDER) * (z + r * d) % Q_ORDER
    return r, s

# ---- generate -------------------------------------------------------------
def main():
    out = __file__.rsplit("/", 2)[0] + "/capture.json"
    if os.path.exists(out) and os.environ.get("FORCE") != "1":
        sys.exit("refusing to overwrite committed capture.json "
                 "(the flag in challenge.yml/flag.py is tied to it); set FORCE=1 "
                 "to regenerate, then update the flag and the private key in flag.py")

    rng = secrets.SystemRandom()
    d = rng.randrange(1, Q_ORDER)
    Q = ec_mul(d, G)

    NBIAS = 60
    sigs = []
    for i in range(NBIAS):
        msg = f"transfer #{i:04d}: pay invoice INV-2026-{i*7+13:05d}"
        # top byte forced to zero -> 0 < k < 2**248
        k = rng.randrange(1, 1 << 248)
        r, s = sign(d, msg, k)
        sigs.append({"msg": msg, "r": hex(r), "s": hex(s)})

    # ---- decoy: identical r, nonces k and (q-k), full range (not biased) ---
    kd = rng.randrange(1 << 248, Q_ORDER)          # full-range nonce
    m1 = "URGENT: release escrow to account 0xC0FFEE"
    m2 = "URGENT: release escrow to account 0xBADF00D"
    r1, s1 = sign(d, m1, kd)
    r2, s2 = sign(d, m2, Q_ORDER - kd)             # same r as sig1
    assert r1 == r2, "decoy r mismatch"
    sigs.append({"msg": m1, "r": hex(r1), "s": hex(s1)})
    sigs.append({"msg": m2, "r": hex(r2), "s": hex(s2)})

    rng2 = secrets.SystemRandom()
    rng2.shuffle(sigs)  # so the decoy is not conveniently at the end

    artifact = {
        "curve": "secp256k1",
        "note": ("ECDSA signatures produced by a hardware wallet with a faulty "
                 "RNG. hash: z = int(sha256(msg)) mod n. "
                 "Public key Q below; recover the private key d."),
        "Q": {"x": hex(Q[0]), "y": hex(Q[1])},
        "n": hex(Q_ORDER),
        "signatures": sigs,
    }
    with open(out, "w") as f:
        json.dump(artifact, f, indent=2)

    flag = "CTF{" + hashlib.sha256(("%064x" % d).encode()).hexdigest()[:32] + "}"
    print("private key d =", hex(d))
    print("num signatures =", len(sigs), "(60 biased + 2 decoy)")
    print("FLAG =", flag)

if __name__ == "__main__":
    main()
