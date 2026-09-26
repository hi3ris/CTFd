#!/usr/bin/env python3
"""Dijkstra shortest path from S to T; read node labels along the path.

The graph.txt header gives node/edge counts and the source/target. Labels are
`L <node> <char>` lines, edges are `E <u> <v> <w>` lines. We run Dijkstra,
reconstruct the path via predecessors, and concatenate the labels.
"""

import heapq
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GRAPH = os.path.join(HERE, "..", "graph.txt")


def main():
    with open(GRAPH, encoding="utf-8") as fh:
        n, _m = map(int, fh.readline().split())
        src, dst = map(int, fh.readline().split())
        labels = [""] * n
        adj = [[] for _ in range(n)]
        for line in fh:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "L":
                labels[int(parts[1])] = parts[2]
            elif parts[0] == "E":
                u, v, w = int(parts[1]), int(parts[2]), int(parts[3])
                adj[u].append((v, w))

    INF = float("inf")
    dist = [INF] * n
    prev = [-1] * n
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        if u == dst:
            break
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    path = []
    cur = dst
    while cur != -1:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    print("".join(labels[node] for node in path))


if __name__ == "__main__":
    main()
