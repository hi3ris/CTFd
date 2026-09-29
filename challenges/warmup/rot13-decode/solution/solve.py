#!/usr/bin/env python3
"""Solver for rot13-decode: apply ROT13 (its own inverse)."""

import codecs
import os

here = os.path.dirname(__file__)
data = open(os.path.join(here, "..", "secret.txt")).read().strip()
print(codecs.decode(data, "rot_13"))
