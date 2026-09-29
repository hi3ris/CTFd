#!/usr/bin/env python3
"""Solver for reverse-string: reverse the characters."""

import os

here = os.path.dirname(__file__)
data = open(os.path.join(here, "..", "backwards.txt")).read().strip()
print(data[::-1])
