#!/usr/bin/env python3
"""Solve the unique Sudoku by backtracking; use its digits to decrypt the flag.

Read the 9 grid rows (0 = empty), solve, flatten the 81 digits row-major, hash
into a SHA-256 keystream, and XOR against CIPHER.
"""

import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PUZZLE = os.path.join(HERE, "..", "puzzle.txt")


def solve(grid):
    # Find the empty cell with the fewest candidates (MRV) for speed.
    best = -1
    best_cand = None
    for i in range(81):
        if grid[i] == 0:
            r, c = divmod(i, 9)
            used = set()
            for k in range(9):
                used.add(grid[r * 9 + k])
                used.add(grid[k * 9 + c])
            br, bc = (r // 3) * 3, (c // 3) * 3
            for dr in range(3):
                for dc in range(3):
                    used.add(grid[(br + dr) * 9 + (bc + dc)])
            cand = [v for v in range(1, 10) if v not in used]
            if best_cand is None or len(cand) < len(best_cand):
                best, best_cand = i, cand
                if len(cand) <= 1:
                    break
    if best == -1:
        return True
    for v in best_cand:
        grid[best] = v
        if solve(grid):
            return True
        grid[best] = 0
    return False


def main():
    cipher = None
    grid = []
    with open(PUZZLE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith("CIPHER"):
                cipher = bytes.fromhex(line.split()[1])
            else:
                grid.extend(int(ch) for ch in line)

    assert solve(grid)
    solution_str = "".join(str(d) for d in grid).encode()
    ks = hashlib.sha256(solution_str).digest()
    while len(ks) < len(cipher):
        ks += hashlib.sha256(ks).digest()
    print(bytes(c ^ k for c, k in zip(cipher, ks)).decode())


if __name__ == "__main__":
    main()
