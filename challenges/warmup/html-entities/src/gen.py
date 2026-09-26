#!/usr/bin/env python3
"""Generate page_snippet.txt: numeric HTML entities of the flag."""

FLAG = "NCTF{ampersand_hash_entities}"
enc = "".join(f"&#{ord(c)};" for c in FLAG)
with open("../page_snippet.txt", "w") as f:
    f.write(enc + "\n")
