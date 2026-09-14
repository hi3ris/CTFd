#!/usr/bin/env python3
"""Solver for binary-ascii: each 8-bit group is one byte."""

import os

here = os.path.dirname(__file__)
data = open(os.path.join(here, "..", "bits.txt")).read().split()
print("".join(chr(int(g, 2)) for g in data))
