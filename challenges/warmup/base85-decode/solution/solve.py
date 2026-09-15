#!/usr/bin/env python3
"""Solver for base85-decode."""

import base64
import os

here = os.path.dirname(__file__)
data = open(os.path.join(here, "..", "secret.txt")).read().strip()
print(base64.b85decode(data).decode())
