#!/usr/bin/env python3
"""Solver for html-entities: unescape numeric HTML entities."""

import html
import os

here = os.path.dirname(__file__)
data = open(os.path.join(here, "..", "page_snippet.txt")).read().strip()
print(html.unescape(data))
