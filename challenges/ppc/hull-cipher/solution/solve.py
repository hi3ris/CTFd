#!/usr/bin/env python3
"""Recover the flag from points.txt by walking the convex hull.

Compute the convex hull (Andrew's monotone chain), orient it counter-clockwise,
rotate so it starts at the bottom-most (then left-most) vertex, and read the
character attached to each hull vertex in order.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
POINTS = os.path.join(HERE, "..", "points.txt")


def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull(points):
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts
    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]  # counter-clockwise, no repeat


def signed_area(poly):
    s = 0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return s


def main():
    charmap = {}
    with open(POINTS, encoding="utf-8") as fh:
        n = int(fh.readline())
        coords = []
        for _ in range(n):
            x, y, ch = fh.readline().split()
            x, y = int(x), int(y)
            coords.append((x, y))
            charmap[(x, y)] = ch

    hull = convex_hull(coords)
    if signed_area(hull) < 0:
        hull.reverse()
    start = min(range(len(hull)), key=lambda i: (hull[i][1], hull[i][0]))
    ordered = hull[start:] + hull[:start]
    flag = "".join(charmap[v] for v in ordered)
    print(flag)


if __name__ == "__main__":
    main()
