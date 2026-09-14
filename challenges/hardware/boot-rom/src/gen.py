#!/usr/bin/env python3
"""Assemble a tiny "boot ROM" for a custom 8-bit VM.

Machine model (see solution/ISA.md, shipped as an artifact):
  * 8 registers R0..R7, all 8-bit (wrap mod 256).
  * One flat byte-addressable memory; the ROM image is loaded at address 0, so
    code and data share the same space.
  * Program counter PC in bytes. Every instruction is exactly 3 bytes:
      opcode, arg1, arg2

Opcodes:
  0x01 LDI  r, imm     r = imm
  0x05 XOR  r, s       r = r ^ Rs
  0x08 OUT  r, _       emit byte Rr
  0x09 JNZ  r, addr    if Rr != 0: PC = addr
  0x0A ADDI r, imm     r = (r + imm) & 0xFF
  0x0B HLT  _, _       stop
  0x0C LDX  r, p       r = mem[Rp]      (indexed load through pointer reg)

The ROM decodes an XOR-obfuscated flag byte-by-byte and OUTs it.
"""

import os

FLAG = b"NCTF{tiny_isa_bootrom_interpreted}"
KEY = 0x5A

OPS = {
    "LDI": 0x01,
    "XOR": 0x05,
    "OUT": 0x08,
    "JNZ": 0x09,
    "ADDI": 0x0A,
    "HLT": 0x0B,
    "LDX": 0x0C,
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, os.pardir, "rom.bin")

    length = len(FLAG)
    # code is 10 instructions * 3 bytes = 30 bytes; data starts at 30
    data_base = 30

    loop = 9  # byte offset of the loop head
    prog = [
        ("LDI", 0, length),  # R0 = count
        ("LDI", 1, KEY),  # R1 = xor key
        ("LDI", 2, data_base),  # R2 = data pointer
        ("LDX", 4, 2),  # @9  R4 = mem[R2]
        ("XOR", 4, 1),  # R4 ^= R1
        ("OUT", 4, 0),  # emit R4
        ("ADDI", 2, 1),  # R2 += 1
        ("ADDI", 0, 0xFF),  # R0 -= 1 (mod 256)
        ("JNZ", 0, loop),  # if R0 != 0 goto @9
        ("HLT", 0, 0),
    ]

    rom = bytearray()
    for mnem, a, b in prog:
        rom += bytes([OPS[mnem], a & 0xFF, b & 0xFF])

    assert len(rom) == data_base, (len(rom), data_base)
    rom += bytes(c ^ KEY for c in FLAG)  # obfuscated flag data

    with open(out, "wb") as f:
        f.write(rom)

    print("wrote", os.path.abspath(out), "size:", len(rom))


if __name__ == "__main__":
    main()
