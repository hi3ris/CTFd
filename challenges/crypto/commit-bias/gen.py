#!/usr/bin/env python3
"""
Generator for the crypto challenge 'commit-bias'.

Story / mechanism (NOT disclosed in the handout):

  The "CoinVault" dealer runs a commit-reveal coin-flip ledger.  Every round it
  produces a field element  y_r in F_p  (the round's "draw"), publishes a
  commitment  C_r = SHA256(y_r || r)[:16]  BEFORE the round, and later opens the
  round by revealing  y_r  so anyone can recheck the commitment.  The published
  "coin" of the round is just  b_r = y_r mod 2.

  The dealer *claims* every draw is an independent fresh sample.  It is not.
  The draws are the output stream of a home-grown multiple-recursive generator
  (an order-k linear recurrence over F_p with SECRET coefficients c_1..c_k):

        y_r = ( c_1*y_{r-1} + c_2*y_{r-2} + ... + c_k*y_{r-k} )  mod p

  The final "vault" round R is committed like every other round, but the game
  ends before it is opened, so y_R is never revealed.  The vault flag blob is
  sealed under  key = SHA256(y_R)  in a SHA256 counter-mode keystream.

  Because the revealed draws obey a fixed linear recurrence, an attacker who
  collects enough opened rounds can recover the (secret) recurrence with
  Berlekamp-Massey over F_p, extrapolate the un-opened draw y_R, verify it
  against the published vault commitment, and derive the key that unseals the
  flag.  No brute force of the 256-bit key/flag is possible; the whole attack
  hinges on noticing that the "independent" draws are linearly dependent.

This generator is deterministic (fixed SEED) so the handout and the static flag
are reproducible.  gen.py is NOT shipped to players (not listed in files:).
"""

import hashlib
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
HANDOUT = os.path.join(HERE, "handout")

# --- fixed knobs -----------------------------------------------------------
SEED       = 20260913          # deterministic build
ORDER_K    = 7                 # secret recurrence order
N_REVEAL   = 48                # opened rounds published in the ledger
VAULT_IDX  = N_REVEAL          # index of the sealed (un-opened) vault round

FLAG = "NCTF{c0mmit_r3v34l_but_th3_dr4ws_w3re_l1n34rly_l1nk3d}"


# --- tiny number theory (no third-party deps) ------------------------------
def is_probable_prime(n, rounds=40):
    if n < 2:
        return False
    small = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    for p in small:
        if n % p == 0:
            return n == p
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    rng = random.Random(0xA11CE)
    for _ in range(rounds):
        a = rng.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def next_prime(n):
    if n % 2 == 0:
        n += 1
    while not is_probable_prime(n):
        n += 2
    return n


# --- Berlekamp-Massey over F_p (used here only to VALIDATE the build) ------
def berlekamp_massey_fp(seq, p):
    """Minimal linear recurrence for seq over F_p (p prime).
    Returns coeffs c with  y_n = sum_{i=1..L} c[i-1]*y_{n-i}  (mod p)."""
    n = len(seq)
    C = [1] + [0] * n         # connection polynomial
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
    # C(x) = 1 + c_1 x + ... + c_L x^L  =>  y_n = -sum_i c_i y_{n-i}
    return [(-C[i]) % p for i in range(1, L + 1)]


def build():
    rng = random.Random(SEED)

    # 256-bit prime, published in the ledger header.
    p = next_prime(rng.getrandbits(256) | (1 << 255) | 1)
    fe_bytes = (p.bit_length() + 7) // 8

    # Secret recurrence: order-k coefficients + k seed draws, all in F_p.
    while True:
        coeffs = [rng.randrange(1, p) for _ in range(ORDER_K)]   # c_1..c_k
        y = [rng.randrange(1, p) for _ in range(ORDER_K)]        # y_0..y_{k-1}
        # generate through the vault index
        while len(y) <= VAULT_IDX:
            r = len(y)
            nxt = 0
            for i in range(1, ORDER_K + 1):
                nxt = (nxt + coeffs[i - 1] * y[r - i]) % p
            y.append(nxt)
        # Validate: the minimal recurrence of the revealed part is exactly
        # order k (non-degenerate), so recovery is unambiguous.
        rec = berlekamp_massey_fp(y[:N_REVEAL], p)
        if len(rec) == ORDER_K and rec == coeffs:
            break

    y_vault = y[VAULT_IDX]

    def commit(val, idx):
        h = hashlib.sha256(val.to_bytes(fe_bytes, "big") + idx.to_bytes(4, "big"))
        return h.digest()[:16]

    def seal(flag_bytes, val):
        key = hashlib.sha256(val.to_bytes(fe_bytes, "big")).digest()
        stream = b""
        ctr = 0
        while len(stream) < len(flag_bytes):
            stream += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
            ctr += 1
        return bytes(a ^ b for a, b in zip(flag_bytes, stream))

    ct = seal(FLAG.encode(), y_vault)

    # --- emit the invented transcript format -------------------------------
    lines = []
    lines.append("COINVAULT-LEDGER v1")
    lines.append("# CoinVault fair-flip ledger export. See SPEC.md to parse.")
    lines.append("P=%x" % p)
    lines.append("ROUNDS=%d" % N_REVEAL)
    lines.append("# opened rounds:  R<idx>|C=<16-byte commit hex>|Y=<draw hex>|B=<coin bit>")
    for r in range(N_REVEAL):
        lines.append("R%03d|C=%s|Y=%x|B=%d" % (
            r, commit(y[r], r).hex(), y[r], y[r] & 1))
    lines.append("# sealed vault round: committed and funded, never opened.")
    lines.append("VAULT|IDX=%d|C=%s|CT=%s" % (
        VAULT_IDX, commit(y_vault, VAULT_IDX).hex(), ct.hex()))
    text = "\n".join(lines) + "\n"

    os.makedirs(HANDOUT, exist_ok=True)
    with open(os.path.join(HANDOUT, "ledger.coinvault"), "w") as f:
        f.write(text)

    print("[gen] prime bits :", p.bit_length())
    print("[gen] fe_bytes   :", fe_bytes)
    print("[gen] order k    :", ORDER_K)
    print("[gen] revealed   :", N_REVEAL)
    print("[gen] y_vault     = %x" % y_vault)
    print("[gen] FLAG       :", FLAG)
    print("[gen] wrote", os.path.join(HANDOUT, "ledger.coinvault"))


if __name__ == "__main__":
    build()
