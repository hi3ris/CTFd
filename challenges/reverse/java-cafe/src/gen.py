#!/usr/bin/env python3
"""
Developer-only generator for the 'java-cafe' reverse challenge.

Compiles src/Vault.java into the shipped artifact Vault.class (JVM bytecode).
Only the compiled .class is distributed to players. This file is NOT shipped.
"""

import os
import shutil
import subprocess


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, os.pardir))
    subprocess.run(["javac", "-d", here, os.path.join(here, "Vault.java")], check=True)
    src = os.path.join(here, "Vault.class")
    dst = os.path.join(root, "Vault.class")
    shutil.move(src, dst)
    print("wrote", dst)


if __name__ == "__main__":
    main()
