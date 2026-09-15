#!/usr/bin/env python3
"""
Static solver for 'obfuscated-strings'.

We read the obfuscated DATA array out of the decompiled StringFog.java in the
APK and reimplement its decode loop. Nothing is hardcoded, so a rebuild solves.

Usage: python3 solve.py [path-to-app.apk]
"""

import re
import sys
import zipfile


def ror8(v: int, r: int) -> int:
    r &= 7
    return ((v >> r) | (v << (8 - r))) & 0xFF if r else v & 0xFF


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../app.apk"
    with zipfile.ZipFile(path) as z:
        src = z.read("sources/com/stashbox/app/StringFog.java").decode()

    block = re.search(r"new int\[\]\s*\{([^}]*)\}", src, re.S).group(1)
    data = [int(x) for x in re.findall(r"-?\d+", block)]

    out = []
    for i, d in enumerate(data):
        x = d ^ 0xA5
        x = ror8(x, (i % 5) + 1)
        x = (x - (i * 7 + 3)) & 0xFF
        out.append(x)
    flag = bytes(out).decode()
    print("flag:", flag)
    assert flag.startswith("NCTF{") and flag.endswith("}")


if __name__ == "__main__":
    main()
