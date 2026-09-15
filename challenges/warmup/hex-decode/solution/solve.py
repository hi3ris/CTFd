#!/usr/bin/env python3
"""Solver for hex-decode."""

import os

here = os.path.dirname(__file__)
data = open(os.path.join(here, "..", "secret.txt")).read().strip()
print(bytes.fromhex(data).decode())
