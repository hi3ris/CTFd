#!/usr/bin/env python3
"""Generate archive.zip with the flag in the archive comment."""

import zipfile

FLAG = "NCTF{look_inside_the_zip_comment}"
with zipfile.ZipFile("../archive.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr(
        "readme.txt",
        "Nothing to see in this file. Have you checked the archive's comment?\n",
    )
    z.comment = FLAG.encode()
