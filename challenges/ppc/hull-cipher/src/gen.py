#!/usr/bin/env python3
"""Generate points.txt for hull-cipher.

The flag characters are placed as points on a large circle (so every one of
them is a vertex of the convex hull), ordered so that walking the hull
counter-clockwise from the bottom-most vertex spells the flag. A cloud of
interior "noise" points with random characters is added as decoys.
"""

import math
import os
import random

FLAG = "NCTF{convex_hull_walks_the_perimeter_ccw}"
R = 1_000_000
NOISE = 400
SEED = 20260914


def build():
    rng = random.Random(SEED)
    pts = []  # (x, y, ch)
    n = len(FLAG)
    # Flag chars on the circle: index 0 at the bottom (angle -90 deg), then
    # counter-clockwise (increasing angle).
    for i, ch in enumerate(FLAG):
        theta = -math.pi / 2 + 2 * math.pi * i / n
        x = round(R * math.cos(theta))
        y = round(R * math.sin(theta))
        pts.append((x, y, ch))
    # Interior noise strictly inside a smaller disk so it can never be a vertex.
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_{}"
    seen = {(x, y) for x, y, _ in pts}
    while len(pts) < n + NOISE:
        rr = rng.uniform(0, R * 0.9)
        ang = rng.uniform(0, 2 * math.pi)
        x = round(rr * math.cos(ang))
        y = round(rr * math.sin(ang))
        if (x, y) in seen:
            continue
        seen.add((x, y))
        pts.append((x, y, rng.choice(alphabet)))
    rng.shuffle(pts)
    return pts


def main():
    pts = build()
    out = os.path.join(os.path.dirname(__file__), "..", "points.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(f"{len(pts)}\n")
        for x, y, ch in pts:
            fh.write(f"{x} {y} {ch}\n")
    print("wrote", os.path.relpath(out), "points:", len(pts))


if __name__ == "__main__":
    main()
