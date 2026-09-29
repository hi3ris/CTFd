#!/usr/bin/env python3
"""
Developer-only generator for the 'pyc-ghost' reverse challenge.

Compiles src/vault.py into the shipped artifact vault.pyc (marshalled CPython
bytecode). No source .py is distributed to players -- only the compiled .pyc.
"""

import os
import py_compile


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "vault.py")
    dst = os.path.join(here, os.pardir, "vault.pyc")
    py_compile.compile(src, cfile=dst, optimize=0)
    print("wrote", os.path.normpath(dst))


if __name__ == "__main__":
    main()
