#!/usr/bin/env python3
"""Search the DFA in automaton.json for its single accepted string."""

import json
import os
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
JSON = os.path.join(HERE, "..", "automaton.json")


def main() -> None:
    with open(JSON, encoding="utf-8") as fh:
        dfa = json.load(fh)

    delta = {}
    for state, sym, nxt in dfa["transitions"]:
        delta[(state, sym)] = nxt
    accept = set(dfa["accept"])
    alphabet = dfa["alphabet"]

    # BFS over states; the accepted language is a single word, so the first
    # accepting state reached carries the flag.
    queue = deque([(dfa["start"], "")])
    seen = {dfa["start"]}
    while queue:
        state, word = queue.popleft()
        if state in accept:
            print(word)
            return
        for sym in alphabet:
            nxt = delta.get((state, sym))
            if nxt is not None and nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, word + sym))
    raise SystemExit("no accepted string found")


if __name__ == "__main__":
    main()
