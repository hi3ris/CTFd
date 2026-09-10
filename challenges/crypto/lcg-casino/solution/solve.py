#!/usr/bin/env python3
"""
Reference solver for lcg-casino.

Strategy
--------
1. Connect; read the banner for the public LCG constants (A, C, M) and deck size.
2. Place a few throwaway calls to collect published shuffles (the reveals).
3. Invert each shuffle (factorial-base encode) back to its rank = top bits of
   that hand's internal state.
4. The number of withheld low bits `L` is not published. Scan L; for each L,
   brute the L hidden low bits of the first observed state and roll the LCG
   forward, keeping the (L, state) that reproduces the next observed ranks.
   Two reveals already pin it uniquely; a third confirms.
5. From the recovered running state, compute each future hand's high card and
   call it. Ten correct calls in a row -> the service pays the flag.

Pure standard library. Usage:
    python3 solve.py <host> <port>
"""
import json
import math
import socket
import sys

DECK_N = 11
FACT = [math.factorial(i) for i in range(DECK_N + 1)]


def encode_rank(perm):
    """Permutation of [0..DECK_N-1] -> lexicographic factorial-base rank."""
    pool = list(range(DECK_N))
    rank = 0
    for i, card in enumerate(perm):
        idx = pool.index(card)
        rank += idx * FACT[DECK_N - 1 - i]
        pool.pop(idx)
    return rank


def decode_shuffle(rank):
    pool, perm, r = list(range(DECK_N)), [], rank
    for i in range(DECK_N):
        base = FACT[DECK_N - 1 - i]
        idx, r = divmod(r, base)
        perm.append(pool.pop(idx))
    return perm


class Conn:
    def __init__(self, host, port):
        self.s = socket.create_connection((host, port), timeout=30)
        self.buf = b""

    def readline(self):
        while b"\n" not in self.buf:
            chunk = self.s.recv(4096)
            if not chunk:
                raise EOFError
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return json.loads(line.decode())

    def send(self, obj):
        self.s.sendall((json.dumps(obj) + "\n").encode())


def recover(A, C, M, ranks, lowbits_candidates):
    """Given consecutive ranks, return (L, state_after_last_observed_rank)."""
    for L in lowbits_candidates:
        r0, r1 = ranks[0], ranks[1]
        for low in range(1 << L):
            x1 = (r0 << L) | low            # candidate full state at obs 0
            x2 = (A * x1 + C) % M           # -> state at obs 1
            if (x2 >> L) != r1:
                continue
            # verify against the remaining observed ranks
            ok = True
            x = x2
            for rk in ranks[2:]:
                x = (A * x + C) % M
                if (x >> L) != rk:
                    ok = False
                    break
            if ok:
                # x is now the state matching ranks[-1]
                return L, x
    return None, None


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9021

    c = Conn(host, port)
    banner = c.readline()
    assert banner["msg"] == "banner", banner
    A, C, M = banner["multiplier"], banner["increment"], banner["modulus"]
    target = banner.get("streak_target", 10)
    print(f"[*] A={A} C={C} M={M} target={target}")
    print(f"[*] commitment (ignored, decoy): {banner['commitment'][:16]}...")

    # Phase 1: collect observations with throwaway calls.
    N_OBS = 3
    ranks = []
    while len(ranks) < N_OBS:
        prompt = c.readline()
        assert prompt["msg"] == "place_call"
        c.send({"call": 0})                 # arbitrary; likely a miss
        rev = c.readline()
        assert rev["msg"] == "reveal"
        ranks.append(encode_rank(rev["shuffle"]))
    print(f"[*] observed ranks: {ranks}")

    # Phase 2: recover (L, state). Scan plausible low-bit counts.
    L, state = recover(A, C, M, ranks, lowbits_candidates=range(8, 25))
    if state is None:
        sys.exit("[!] recovery failed")
    print(f"[+] recovered: L={L} state={state}")

    # Phase 3: call the future exactly.
    wins = 0
    while True:
        prompt = c.readline()
        if prompt.get("msg") == "jackpot":
            print(f"[+] FLAG: {prompt['flag']}")
            return
        assert prompt["msg"] == "place_call"
        state = (A * state + C) % M         # next hand's state
        call = decode_shuffle(state >> L)[0]  # predicted high card
        c.send({"call": call})
        rev = c.readline()
        if rev.get("msg") == "jackpot":
            print(f"[+] FLAG: {rev['flag']}")
            return
        assert rev["msg"] == "reveal", rev
        if rev["result"] == "WIN":
            wins += 1
        else:
            print(f"[!] miss at hand {rev['hand']} (call={call}, "
                  f"high={rev['high_card']}) -- state desync, aborting")
            sys.exit(1)
        print(f"[*] hand {rev['hand']}: WIN streak={rev['streak']}")
        # Some builds send the jackpot as a separate line after the winning
        # reveal; loop will pick it up on the next readline.
        if rev["streak"] >= target:
            nxt = c.readline()
            if nxt.get("msg") == "jackpot":
                print(f"[+] FLAG: {nxt['flag']}")
                return


if __name__ == "__main__":
    main()
