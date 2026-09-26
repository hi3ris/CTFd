#!/usr/bin/env python3
"""Emit automaton.json for dfa-oracle.

We build a DFA that accepts exactly one string -- the flag. A linear chain of
states spells the flag; every other transition drops into a non-accepting trap
state. States are given opaque ids and the transition list is shuffled so the
chain is not obvious by eye; the solver must actually search the automaton.
"""

import json
import os
import random

FLAG = "NCTF{regular_languages_have_one_word}"


def main() -> None:
    rng = random.Random(90909)
    alphabet = sorted(set(FLAG))

    # Opaque names for the chain states plus a trap.
    names = [f"s{rng.randrange(10**6):06d}" for _ in range(len(FLAG) + 1)]
    while len(set(names)) != len(names):
        names = [f"s{rng.randrange(10**6):06d}" for _ in range(len(FLAG) + 1)]
    trap = "s999999"

    start = names[0]
    accept = names[-1]

    transitions = []  # (state, symbol, next_state)
    for i in range(len(FLAG)):
        cur, nxt = names[i], names[i + 1]
        for sym in alphabet:
            transitions.append([cur, sym, nxt if sym == FLAG[i] else trap])
    # Accept and trap states loop on the trap for every symbol.
    for state in (accept, trap):
        for sym in alphabet:
            transitions.append([state, sym, trap])

    rng.shuffle(transitions)

    dfa = {
        "alphabet": alphabet,
        "states": sorted(set(names + [trap])),
        "start": start,
        "accept": [accept],
        "transitions": transitions,
    }
    out = os.path.join(os.path.dirname(__file__), "..", "automaton.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(dfa, fh, indent=2)
    print("wrote", os.path.relpath(out), "states:", len(dfa["states"]))


if __name__ == "__main__":
    main()
