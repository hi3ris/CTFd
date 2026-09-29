#!/usr/bin/env python3
"""Reference solver for boot-rom.

Implement the 3-byte-per-instruction VM described in ISA.md, load rom.bin at
address 0, run until HLT, and collect the bytes produced by OUT.
"""

import os
import sys


def run(rom):
    mem = bytearray(256)
    mem[: len(rom)] = rom
    reg = [0] * 8
    pc = 0
    out = bytearray()
    steps = 0
    while steps < 100000:
        steps += 1
        op, a, b = mem[pc], mem[pc + 1], mem[pc + 2]
        nxt = pc + 3
        if op == 0x01:  # LDI r, imm
            reg[a] = b & 0xFF
        elif op == 0x05:  # XOR r, s
            reg[a] ^= reg[b]
        elif op == 0x08:  # OUT r
            out.append(reg[a] & 0xFF)
        elif op == 0x09:  # JNZ r, addr
            if reg[a] != 0:
                nxt = b
        elif op == 0x0A:  # ADDI r, imm
            reg[a] = (reg[a] + b) & 0xFF
        elif op == 0x0B:  # HLT
            break
        elif op == 0x0C:  # LDX r, p  ->  r = mem[Rp]
            reg[a] = mem[reg[b]]
        else:
            raise ValueError(f"bad opcode 0x{op:02x} at pc={pc}")
        pc = nxt
    return bytes(out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, os.pardir, "rom.bin")
    with open(path, "rb") as f:
        rom = f.read()
    print(run(rom).decode("ascii", "replace"))


if __name__ == "__main__":
    main()
