#!/usr/bin/env python3
"""
casino_core -- the "provably fair" shuffle used by lcg-casino.

This module is intentionally shippable/public: a provably-fair casino publishes
its shuffle algorithm and its RNG parameters. The ONLY secret is the per-instance
seed (the internal LCG state), which is committed to via SHA-256 at connect time
but never revealed. Recovering that hidden state from the published shuffles is
the whole challenge.

RNG: a truncated linear congruential generator.

    state_{n+1} = (A * state_n + C) mod M          (M = 2**40)

Each hand advances the state once and publishes ONLY the top 24 bits of the new
state, encoded as a shuffle of an 11-card deck. The low LOWBITS bits of every
state are never published -- that truncation is what makes recovery non-trivial.

The "rank" (top 24 bits) is turned into a deck order with a plain factorial-base
(Lehmer) decode in *lexicographic* order over the pool [0..10]. Because
2**24 < 11!  ( 16,777,216 < 39,916,800 ) every 24-bit rank is a valid, unique
permutation index, so a published order maps back to exactly one rank.

The number of hidden low bits (LOWBITS) and the rule that picks the "high card"
out of the order are deliberately NOT stated in the handout spec -- they are
short inferences from the published sample transcript.
"""
import math

# --- Public RNG parameters (published in the banner and SPEC.md) -----------
M = 1 << 40                 # modulus 2**40
A = 2654435761             # multiplier (A % 4 == 1)
C = 3039632973             # increment  (C is odd)  -> full period 2**40

# --- Public deck / encoding ------------------------------------------------
DECK_N = 11                # 11-card deck, labels 0..10

# --- Withheld from the spec (inferable from the sample transcript) ----------
LOWBITS = 16               # hidden low bits; rank = state >> LOWBITS in [0, 2**24)

_FACT = [math.factorial(i) for i in range(DECK_N + 1)]


def advance(state: int) -> int:
    """One LCG step."""
    return (A * state + C) % M


def rank_of(state: int) -> int:
    """The published rank = top (40 - LOWBITS) bits of the state."""
    return state >> LOWBITS


def decode_shuffle(rank: int) -> list:
    """Factorial-base (lexicographic) decode of `rank` into a permutation of
    [0 .. DECK_N-1]. `rank` must be < DECK_N!."""
    pool = list(range(DECK_N))
    perm = []
    r = rank
    for i in range(DECK_N):
        base = _FACT[DECK_N - 1 - i]
        idx = r // base
        r %= base
        perm.append(pool.pop(idx))
    return perm


def high_card(perm: list) -> int:
    """The 'high card' of a dealt order is the first card off the deck."""
    return perm[0]


def deal(state: int):
    """Advance the state once and return (new_state, shuffle, high_card)."""
    state = advance(state)
    perm = decode_shuffle(rank_of(state))
    return state, perm, high_card(perm)
