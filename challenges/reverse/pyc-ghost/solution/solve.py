#!/usr/bin/env python3
"""
Static solver for 'pyc-ghost'.

The artifact is a marshalled CPython .pyc. We unmarshal its top-level code
object, execute it in an isolated namespace (the `if __name__ == "__main__"`
guard keeps main() from running), and call the reconstruction routine to recover
the flag. The flag is never stored: it is rebuilt from DATA XOR an LCG keystream.

This is exactly what a reverser does after decompiling the .pyc; you could also
reimplement the LCG by hand from the constants in the disassembly.

Usage: python3 solve.py [path-to-vault.pyc]
"""

import marshal
import sys


def load_code(path):
    data = open(path, "rb").read()
    # .pyc header is 16 bytes for CPython 3.7+ (magic, flags, mtime/size fields).
    return marshal.loads(data[16:])


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../vault.pyc"
    code = load_code(path)
    ns = {"__name__": "vault_solved"}
    exec(code, ns)
    flag = ns["unlock"]()
    print("flag:", flag.decode())


if __name__ == "__main__":
    main()
