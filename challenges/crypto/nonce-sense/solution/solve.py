#!/usr/bin/env python3
"""
Solver for 'nonce-sense'.

Attack: ECDSA with an 8-bit-biased nonce (top byte of every k is zero) is a
Hidden Number Problem.  With  k_i = a_i + t_i*d (mod n),  0 < k_i < 2**248,
the vector of nonces is an unusually short vector of a lattice; LLL recovers it
and hence the private key d.

Everything here is pure Python (no sage / fpylll), including a self-contained
LLL.  The two signatures that share an identical r are the decoy (nonces k and
n-k, NOT a reused nonce) and are dropped before building the lattice.

Usage:  python3 solve.py [../capture.json]
"""
import sys, json, hashlib

# ---- secp256k1 ------------------------------------------------------------
P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
A  = 0
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G  = (Gx, Gy)

def ec_add(Pt, Qt):
    if Pt is None: return Qt
    if Qt is None: return Pt
    x1, y1 = Pt; x2, y2 = Qt
    if x1 == x2 and (y1 + y2) % P == 0: return None
    if Pt == Qt:
        lam = (3 * x1 * x1 + A) * pow(2 * y1, -1, P) % P
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, P) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)

def ec_mul(k, Pt):
    R = None; k %= N
    while k:
        if k & 1: R = ec_add(R, Pt)
        Pt = ec_add(Pt, Pt); k >>= 1
    return R

def h_of(msg): return int.from_bytes(hashlib.sha256(msg.encode()).digest(), "big") % N

# ---- pure-python integer LLL (de Weger / Cohen Alg. 2.6.7, delta = 3/4) ----
# Exact integer arithmetic only -> no fraction blow-up, fast enough in pure
# Python for the ~50-dimensional lattice this attack needs.
def lll(basis):
    b = [None] + [row[:] for row in basis]        # 1-indexed
    n = len(basis)
    def dot(u, v): return sum(x * y for x, y in zip(u, v))
    d = [0] * (n + 1); d[0] = 1
    lam = [[0] * (n + 1) for _ in range(n + 1)]

    def red(k, l):
        if 2 * abs(lam[k][l]) <= d[l]:
            return
        q = (2 * lam[k][l] + d[l]) // (2 * d[l])   # nearest integer of lam/d[l]
        b[k] = [x - q * y for x, y in zip(b[k], b[l])]
        lam[k][l] -= q * d[l]
        for i in range(1, l):
            lam[k][i] -= q * lam[l][i]

    def swap(k, kmax):
        b[k], b[k - 1] = b[k - 1], b[k]
        for j in range(1, k - 1):
            lam[k][j], lam[k - 1][j] = lam[k - 1][j], lam[k][j]
        L = lam[k][k - 1]
        B = (d[k - 2] * d[k] + L * L) // d[k - 1]
        for i in range(k + 1, kmax + 1):
            t = lam[i][k]
            lam[i][k] = (d[k] * lam[i][k - 1] - L * t) // d[k - 1]
            lam[i][k - 1] = (B * t + L * lam[i][k]) // d[k]
        d[k - 1] = B

    d[1] = dot(b[1], b[1])
    k = 2; kmax = 1
    while k <= n:
        if k > kmax:                               # incremental Gram-Schmidt
            kmax = k
            for j in range(1, k + 1):
                u = dot(b[k], b[j])
                for i in range(1, j):
                    u = (d[i] * u - lam[k][i] * lam[j][i]) // d[i - 1]
                if j < k:
                    lam[k][j] = u
                else:
                    d[k] = u
        red(k, k - 1)
        if 4 * d[k] * d[k - 2] < 3 * d[k - 1] * d[k - 1] - 4 * lam[k][k - 1] ** 2:
            swap(k, kmax)
            k = max(k - 1, 2)
        else:
            for l in range(k - 2, 0, -1):
                red(k, l)
            k += 1
    return b[1:]

# ---- HNP attack -----------------------------------------------------------
def solve(path):
    art = json.load(open(path))
    sigs = art["signatures"]
    Qx = int(art["Q"]["x"], 16); Qy = int(art["Q"]["y"], 16)
    Qpub = (Qx, Qy)

    # Drop the decoy: any r that appears more than once (k / n-k share r).
    from collections import Counter
    rc = Counter(int(sg["r"], 16) for sg in sigs)
    good = [sg for sg in sigs if rc[int(sg["r"], 16)] == 1]
    print(f"[*] {len(sigs)} signatures, {len(sigs)-len(good)} dropped as equal-r decoy, "
          f"{len(good)} biased signatures used")

    m = min(52, len(good))        # subset size for the lattice
    sub = good[:m]
    B_bound = 1 << 248             # 0 < k < 2**248

    t = []; a = []
    for sg in sub:
        r = int(sg["r"], 16); s = int(sg["s"], 16); z = h_of(sg["msg"])
        sinv = pow(s, -1, N)
        t.append(r * sinv % N)
        a.append(z * sinv % N)

    # Integer lattice (dim m+2), scale = N so entries stay integers:
    #   rows 0..m-1 : N^2 * e_i
    #   row m       : [N*t_0 ... N*t_{m-1}, B, 0]
    #   row m+1     : [N*a_0 ... N*a_{m-1}, 0, N*B]
    # Target vector ~ (N*k_0, ..., N*k_{m-1}, d*B, N*B), all ~2^504 => short.
    dim = m + 2
    M = [[0] * dim for _ in range(dim)]
    for i in range(m):
        M[i][i] = N * N
    for i in range(m):
        M[m][i]   = N * t[i]
        M[m + 1][i] = N * a[i]
    M[m][m]       = B_bound
    M[m + 1][m + 1] = N * B_bound

    print("[*] running LLL on a", dim, "x", dim, "lattice ...")
    R = lll(M)

    # Recover d: for each reduced row, each sign, each index j, turn the
    # candidate nonce back into a private key and check against the public key.
    for row in R:
        for sign in (1, -1):
            for j in range(m):
                kj = sign * row[j]
                if kj % N == 0:
                    continue
                kj //= N
                if not (0 < kj < B_bound):
                    continue
                try:
                    d = (kj - a[j]) * pow(t[j], -1, N) % N
                except ValueError:
                    continue
                if ec_mul(d, G) == Qpub:
                    flag = "CTF{" + hashlib.sha256(("%064x" % d).encode()).hexdigest()[:32] + "}"
                    print("[+] private key d =", hex(d))
                    print("[+] FLAG =", flag)
                    return d, flag
    print("[-] recovery failed (try a larger subset m)")
    return None

if __name__ == "__main__":
    solve(sys.argv[1] if len(sys.argv) > 1 else "../capture.json")
