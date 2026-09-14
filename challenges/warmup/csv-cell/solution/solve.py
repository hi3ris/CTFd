#!/usr/bin/env python3
"""Solver for csv-cell: find the cell containing the flag."""

import csv
import os

here = os.path.dirname(__file__)
with open(os.path.join(here, "..", "roster.csv")) as f:
    for row in csv.reader(f):
        for cell in row:
            if cell.startswith("NCTF{"):
                print(cell)
