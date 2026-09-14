#!/usr/bin/env python3
"""Generate puzzle.txt for sudoku-vault.

Build a full valid 9x9 Sudoku, then dig holes while a solution-counting solver
confirms the puzzle still has EXACTLY one solution. The unique solution's 81
digits (row-major) seed a SHA-256 keystream that XOR-encrypts the flag, so only
the correct completion decrypts it.
"""

import hashlib
import os
import random

FLAG = "NCTF{backtracking_sudoku_is_unique_here}"
SEED = 8080


def solve_count(grid, limit=2):
    """Count solutions up to `limit` (backtracking)."""
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
            total = 0
            for v in range(1, 10):
                if v not in used:
                    grid[i] = v
                    total += solve_count(grid, limit - total)
                    if total >= limit:
                        grid[i] = 0
                        return total
            grid[i] = 0
            return total
    return 1


def build_full(rng):
    grid = [0] * 81

    def fill(pos):
        if pos == 81:
            return True
        r, c = divmod(pos, 9)
        used = set()
        for k in range(9):
            used.add(grid[r * 9 + k])
            used.add(grid[k * 9 + c])
        br, bc = (r // 3) * 3, (c // 3) * 3
        for dr in range(3):
            for dc in range(3):
                used.add(grid[(br + dr) * 9 + (bc + dc)])
        vals = [v for v in range(1, 10) if v not in used]
        rng.shuffle(vals)
        for v in vals:
            grid[pos] = v
            if fill(pos + 1):
                return True
        grid[pos] = 0
        return False

    fill(0)
    return grid


def main():
    rng = random.Random(SEED)
    full = build_full(rng)

    puzzle = full[:]
    order = list(range(81))
    rng.shuffle(order)
    for i in order:
        saved = puzzle[i]
        puzzle[i] = 0
        if solve_count(puzzle[:], 2) != 1:
            puzzle[i] = saved  # removing broke uniqueness; keep the clue

    solution_str = "".join(str(d) for d in full).encode()
    ks = hashlib.sha256(solution_str).digest()
    while len(ks) < len(FLAG):
        ks += hashlib.sha256(ks).digest()
    cipher = bytes(ord(c) ^ k for c, k in zip(FLAG, ks))

    clues = sum(1 for d in puzzle if d)
    out = os.path.join(os.path.dirname(__file__), "..", "puzzle.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("CIPHER " + cipher.hex() + "\n")
        for r in range(9):
            fh.write("".join(str(puzzle[r * 9 + c]) for c in range(9)) + "\n")
    print("wrote", os.path.relpath(out), "clues:", clues)


if __name__ == "__main__":
    main()
