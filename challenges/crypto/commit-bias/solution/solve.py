#!/usr/bin/env python3
"""
Reference solver for 'commit-bias'.

The ledger opens 48 rounds of a commit-reveal coin flip, each revealing a field
element Y_r in F_p, and commits to (but never opens) a final "vault" round.

The break: the "independent" per-round draws are NOT independent -- they are the
output of an order-k linear recurrence over F_p with secret coefficients:

        y_r = ( c_1*y_{r-1} + ... + c_k*y_{r-k} )  (mod p)

So the opened draws let us recover that hidden recurrence (Berlekamp-Massey over
F_p), extrapolate the un-opened vault draw y_R, confirm it against the published
vault commitment, and derive  key = SHA256(y_R)  which unseals the flag blob.

Pure standard library, runs in well under a second.

Usage:  python3 solve.py [../handout/ledger.coinvault]
"""
import hashlib
import os
import sys


def berlekamp_massey_fp(seq, p):
    """Minimal linear recurrence for seq over F_p (p prime).
    Returns coeffs c with  y_n = sum_{i=1..L} c[i-1]*y_{n-i}  (mod p)."""
    n = len(seq)
    C = [1] + [0] * n
    B = [1] + [0] * n
    L, m, b = 0, 1, 1
    for i in range(n):
        d = seq[i] % p
        for j in range(1, L + 1):
            d = (d + C[j] * seq[i - j]) % p
        if d == 0:
            m += 1
            continue
        coef = d * pow(b, -1, p) % p
        T = C[:]
        for j in range(n + 1 - m):
            C[j + m] = (C[j + m] - coef * B[j]) % p
        if 2 * L <= i:
            L = i + 1 - L
            B = T
            b = d
            m = 1
        else:
            m += 1
    return [(-C[i]) % p for i in range(1, L + 1)]


def parse(path):
    p = None
    reveals = {}          # idx -> Y
    commits = {}          # idx -> 16-byte commit
    vault = None          # (idx, commit_bytes, ct_bytes)
    for raw in open(path):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("COINVAULT"):
            continue
        if line.startswith("P="):
            p = int(line[2:], 16)
        elif line.startswith("ROUNDS="):
            pass
        elif line.startswith("R") and "|" in line:
            parts = line.split("|")
            idx = int(parts[0][1:])
            fields = dict(kv.split("=", 1) for kv in parts[1:])
            commits[idx] = bytes.fromhex(fields["C"])
            reveals[idx] = int(fields["Y"], 16)
        elif line.startswith("VAULT"):
            parts = line.split("|")
            fields = dict(kv.split("=", 1) for kv in parts[1:])
            vault = (int(fields["IDX"]),
                     bytes.fromhex(fields["C"]),
                     bytes.fromhex(fields["CT"]))
    return p, reveals, commits, vault


def commit(val, idx, fe_bytes):
    return hashlib.sha256(val.to_bytes(fe_bytes, "big")
                          + idx.to_bytes(4, "big")).digest()[:16]


def unseal(ct, val, fe_bytes):
    key = hashlib.sha256(val.to_bytes(fe_bytes, "big")).digest()
    stream = b""
    ctr = 0
    while len(stream) < len(ct):
        stream += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(a ^ b for a, b in zip(ct, stream))


def solve(path):
    p, reveals, commits, vault = parse(path)
    fe_bytes = (p.bit_length() + 7) // 8
    idxs = sorted(reveals)
    seq = [reveals[i] for i in idxs]

    # sanity: every opened commitment must match its revealed draw
    for i in idxs:
        assert commit(reveals[i], i, fe_bytes) == commits[i], f"bad commit @{i}"
    print(f"[*] parsed {len(seq)} opened draws over a {p.bit_length()}-bit field; "
          f"all commitments verify")

    # recover the hidden linear recurrence from the opened stream
    coeffs = berlekamp_massey_fp(seq, p)
    k = len(coeffs)
    print(f"[*] recovered a hidden order-{k} linear recurrence over F_p")

    # confirm it reproduces every remaining opened draw (no free lunch)
    for r in range(k, len(seq)):
        pred = sum(coeffs[i - 1] * seq[r - i] for i in range(1, k + 1)) % p
        assert pred == seq[r], f"recurrence check failed @{r}"
    print("[*] recurrence reproduces all opened draws")

    # extrapolate the sequence up to (and including) the un-opened vault round
    vault_idx, vault_commit, ct = vault
    y = list(seq)
    while len(y) <= vault_idx:
        r = len(y)
        y.append(sum(coeffs[i - 1] * y[r - i] for i in range(1, k + 1)) % p)
    y_vault = y[vault_idx]

    # the vault commitment is the proof our prediction is right
    assert commit(y_vault, vault_idx, fe_bytes) == vault_commit, \
        "predicted vault draw does not match its published commitment"
    print(f"[+] predicted sealed draw y_{vault_idx} matches the vault commitment")

    flag = unseal(ct, y_vault, fe_bytes).decode()
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    default = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "handout", "ledger.coinvault")
    solve(sys.argv[1] if len(sys.argv) > 1 else default)
