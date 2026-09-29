#!/usr/bin/env python3
"""Generate graph.txt for dijkstra-relay.

A weighted directed graph. A "spine" path S -> ... -> T uses only weight-1
edges and is the UNIQUE shortest path; every other edge is heavy (>= 500), so
any deviation is strictly more expensive. Each node carries a label character;
reading the labels along the shortest path spells the flag.
"""

import os
import random

FLAG = "NCTF{dijkstra_relay_spells_the_route}"
SEED = 777
DECOY_EDGES = 1200


def main():
    rng = random.Random(SEED)
    n_spine = len(FLAG)
    n_extra = 120
    total = n_spine + n_extra

    # Assign a shuffled id to every node so the spine is not 0..L-1 in the file.
    ids = list(range(total))
    rng.shuffle(ids)
    spine_ids = ids[:n_spine]  # spine_ids[i] carries label FLAG[i]

    labels = {}
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_{}"
    for i, nid in enumerate(spine_ids):
        labels[nid] = FLAG[i]
    for nid in ids[n_spine:]:
        labels[nid] = rng.choice(alphabet)

    src, dst = spine_ids[0], spine_ids[-1]

    edges = set()
    # Spine: consecutive weight-1 edges.
    for i in range(n_spine - 1):
        edges.add((spine_ids[i], spine_ids[i + 1], 1))

    # Heavy decoy edges (weight >= 500). Never add a weight-1 edge elsewhere,
    # so the all-1 spine (cost n_spine-1 < 500) stays uniquely shortest.
    while len([e for e in edges if e[2] != 1]) < DECOY_EDGES:
        u = rng.randrange(total)
        v = rng.randrange(total)
        if u == v:
            continue
        w = rng.randint(500, 5000)
        if any(a == u and b == v for a, b, _ in edges):
            continue
        edges.add((u, v, w))

    edges = list(edges)
    rng.shuffle(edges)

    out = os.path.join(os.path.dirname(__file__), "..", "graph.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(f"{total} {len(edges)}\n")
        fh.write(f"{src} {dst}\n")
        for nid in range(total):
            fh.write(f"L {nid} {labels[nid]}\n")
        for u, v, w in edges:
            fh.write(f"E {u} {v} {w}\n")
    print("wrote", os.path.relpath(out), "nodes:", total, "edges:", len(edges))


if __name__ == "__main__":
    main()
