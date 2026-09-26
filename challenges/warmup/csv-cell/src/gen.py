#!/usr/bin/env python3
"""Generate roster.csv with the flag tucked into one cell."""

import csv

FLAG = "NCTF{hidden_in_one_cell}"
rows = [
    ["id", "name", "role", "note"],
    ["1", "Ama", "player", "warming up"],
    ["2", "Kofi", "player", "ready"],
    ["3", "Zoe", "admin", FLAG],
    ["4", "Yao", "player", "good luck"],
]
with open("../roster.csv", "w", newline="") as f:
    csv.writer(f).writerows(rows)
