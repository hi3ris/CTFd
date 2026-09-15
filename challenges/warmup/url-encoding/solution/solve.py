#!/usr/bin/env python3
"""Solver for url-encoding: percent-decode."""

import os
import urllib.parse

here = os.path.dirname(__file__)
data = open(os.path.join(here, "..", "encoded.txt")).read().strip()
print(urllib.parse.unquote(data))
