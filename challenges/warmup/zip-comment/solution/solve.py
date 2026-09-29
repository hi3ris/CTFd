#!/usr/bin/env python3
"""Solver for zip-comment: read the archive-level comment."""

import os
import zipfile

here = os.path.dirname(__file__)
with zipfile.ZipFile(os.path.join(here, "..", "archive.zip")) as z:
    print(z.comment.decode())
