#!/usr/bin/env python3
"""Solver for base64-decode: base64-decode secret.txt."""

import base64
import os

here = os.path.dirname(__file__)
data = open(os.path.join(here, "..", "secret.txt")).read().strip()
print(base64.b64decode(data).decode())
