#!/usr/bin/env python3
"""Reference solver for web-invoicer-protopoll -- STUB. TODO: implement the exploit chain and
print the recovered flag.

    python3 solve.py http://HOST:PORT
"""
import sys


def solve(base):
    raise SystemExit("solver not implemented for web-invoicer-protopoll")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
