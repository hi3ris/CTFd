#!/usr/bin/env python3
"""
lcg-casino -- a per-team "provably fair" casino served over a small line-based
JSON protocol on a raw TCP socket. It is NOT HTTP; you speak the framing
yourself (one JSON object per line, UTF-8, '\n' terminated).

WHY THERE IS NO DOWNLOADABLE FLAG
---------------------------------
The flag is emitted by the RUNNING service and only after a verifiable EFFECT:
you correctly call the high card for STREAK_TARGET hands in a row against a live,
per-instance RNG. There is no payload shape to guess and nothing to brute
offline -- the service checks the effect (you predicted the hidden future), not
any method. A blind guesser hits 10 straight calls with probability
(1/11)**10 ~= 4e-11, so the streak is a sound oracle that you actually broke the
generator.

HOW A HAND WORKS
----------------
  1. Server -> {"msg":"place_call","hand":n,"streak":s}
  2. You    -> {"call": <int 0..10>}        (your call, BEFORE the deal)
  3. Server advances the LCG, deals the shuffle, then reveals it:
       {"msg":"reveal","hand":n,"shuffle":[...],"high_card":h,
        "your_call":c,"result":"WIN"|"MISS","streak":s'}
  4. A miss resets the streak to 0. Hands are unlimited.
  5. On reaching STREAK_TARGET straight wins:
       {"msg":"jackpot","flag":"NCTF{...}"}

The reveal of each completed hand is your only information channel: the shuffle
encodes the top bits of that hand's internal state, and consecutive hands' states
are LCG-linked. Two or three reveals are enough to recover the full hidden state
(low bits included) and then call every future hand exactly.

SECRETS
-------
  * FLAG / CHALLENGE_SECRET (env)  -> the per-challenge flag, resolved via
                          flag.get_flag(). Never on the crypto path.
  * SEED (os.urandom)  -> the initial LCG state. Fresh per connection. Committed
                          to via SHA-256 in the banner but NEVER revealed. You do
                          not need the seed; you recover the *state* from outputs.
"""
import hashlib
import json
import os
import socketserver
import threading

import casino_core as core
import flag as flag_mod

CHALLENGE_ID = "crypto-lcg-casino"

STREAK_TARGET = 10
DECK_N = core.DECK_N
BIND_HOST = os.environ.get("BIND_HOST", "0.0.0.0")
BIND_PORT = int(os.environ.get("BIND_PORT", "9021"))

# Per-connection idle / total limits so nothing hangs a worker forever.
IDLE_TIMEOUT = 120.0
MAX_HANDS = 100000


def compute_flag() -> str:
    # Per-challenge contract: FLAG if injected, else NCTF{CHALLENGE_SECRET[:24]},
    # else a local-dev fallback. No runtime dependence on TEAM_SECRET.
    return flag_mod.get_flag()


class Handler(socketserver.BaseRequestHandler):
    def _send(self, obj):
        self.request.sendall((json.dumps(obj) + "\n").encode())

    def _readline(self):
        buf = b""
        while b"\n" not in buf:
            chunk = self.request.recv(4096)
            if not chunk:
                return None
            buf += chunk
            if len(buf) > 65536:  # a call is tiny; anything huge is abuse
                return None
        return buf.split(b"\n", 1)[0]

    def handle(self):
        self.request.settimeout(IDLE_TIMEOUT)

        # Fresh hidden state per connection. The commitment is published; the
        # seed is not. Note the seed also seeds nothing else -- there is no
        # preimage shortcut here, the LCG structure is the way in.
        state = int.from_bytes(os.urandom(5), "big")  # 40-bit seed
        commitment = hashlib.sha256(state.to_bytes(5, "big")).hexdigest()

        banner = {
            "msg": "banner",
            "game": "Provably-Fair Rail Casino",
            "challenge": CHALLENGE_ID,
            "rng": "truncated-LCG",
            "modulus": core.M,
            "multiplier": core.A,
            "increment": core.C,
            "deck": DECK_N,
            "shuffle": ("factorial-base (lexicographic) decode of the published "
                        "rank into a permutation of [0..deck-1]; see SPEC.md"),
            "commitment": commitment,
            "commitment_note": ("SHA-256 of the secret seed, published for "
                                "auditability. The seed itself is never revealed."),
            "streak_target": STREAK_TARGET,
            "flag_format": "NCTF{...}",
            "rules": ("Each hand: send your call for the HIGH card, then the "
                      "hand is dealt and the full shuffle is published. Land "
                      f"{STREAK_TARGET} correct calls in a row to take the "
                      "jackpot. Any miss resets the streak to 0. Hands are "
                      "unlimited."),
            "protocol": ("line-delimited JSON. Reply to each place_call with "
                         '{"call": <int 0..deck-1>}.'),
        }
        self._send(banner)

        streak = 0
        for hand in range(1, MAX_HANDS + 1):
            self._send({"msg": "place_call", "hand": hand, "streak": streak})

            line = self._readline()
            if line is None:
                return
            try:
                msg = json.loads(line.decode())
                call = int(msg["call"])
            except Exception:
                self._send({"msg": "error",
                            "detail": 'expected {"call": <int 0..%d>}' % (DECK_N - 1)})
                # Treat a malformed call as an automatic miss so the protocol
                # stays in lockstep; it costs nothing but the streak.
                call = -1

            state, perm, high = core.deal(state)
            win = (call == high)
            streak = streak + 1 if win else 0

            self._send({
                "msg": "reveal",
                "hand": hand,
                "shuffle": perm,
                "high_card": high,
                "your_call": call,
                "result": "WIN" if win else "MISS",
                "streak": streak,
            })

            if streak >= STREAK_TARGET:
                self._send({"msg": "jackpot", "flag": compute_flag()})
                return


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    srv = Server((BIND_HOST, BIND_PORT), Handler)
    print(f"lcg-casino listening on {BIND_HOST}:{BIND_PORT}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
