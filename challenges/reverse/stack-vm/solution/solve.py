#!/usr/bin/env python3
"""
Static solver for 'stack-vm'.

The VM is a per-byte accumulator machine driven by an embedded bytecode program.
Disassembling `prog` (in the binary's .rodata) gives:

    XOR 0x3D ; ADD 0x11 ; ROL 3 ; XORI ; SUB 0x07 ; ROR 2 ; HALT

so the per-byte transform applied at position i is:

    y = ROR8( ((ROL8(((x ^ 0x3D) + 0x11) & 0xFF, 3) ^ i) - 0x07) & 0xFF, 2 )

Every op is invertible, so target[i] maps straight back to key[i]. Then the flag
is flag_enc XOR key (key repeated). We do NOT hardcode the flag, key, or their
offsets: we slide over the binary, invert each window to a candidate key, and
keep the window whose key decrypts another window to NCTF{...}.

Usage: python3 solve.py [path-to-chall]
"""

import sys

# Program recovered by disassembling `prog` in the binary. (op, imm)
PROGRAM = [(0x01, 0x3D), (0x02, 0x11), (0x04, 3), (0x06, None), (0x03, 0x07), (0x05, 2)]


def rol8(v, r):
    r &= 7
    return ((v << r) | (v >> (8 - r))) & 0xFF


def ror8(v, r):
    r &= 7
    return ((v >> r) | (v << (8 - r))) & 0xFF


def invert(i, y):
    """Map a target byte back to the key byte at position i."""
    acc = y & 0xFF
    for op, imm in reversed(PROGRAM):
        if op == 0x01:  # XOR
            acc ^= imm
        elif op == 0x02:  # ADD -> subtract
            acc = (acc - imm) & 0xFF
        elif op == 0x03:  # SUB -> add
            acc = (acc + imm) & 0xFF
        elif op == 0x04:  # ROL -> ROR
            acc = ror8(acc, imm)
        elif op == 0x05:  # ROR -> ROL
            acc = rol8(acc, imm)
        elif op == 0x06:  # XORI
            acc ^= i & 0xFF
    return acc


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../chall"
    data = open(path, "rb").read()
    n = len(data)

    for klen in range(8, 40):
        for toff in range(n - klen):
            key = bytearray()
            for i in range(klen):
                b = invert(i, data[toff + i])
                if not (0x20 <= b < 0x7F):
                    break
                key.append(b)
            if len(key) != klen:
                continue
            # candidate key: does some window decrypt to NCTF{...}?
            for foff in range(n - 5):
                if bytes(data[foff + i] ^ key[i % klen] for i in range(5)) != b"NCTF{":
                    continue
                out = bytearray(b"NCTF{")
                for i in range(5, 96):
                    if foff + i >= n:
                        break
                    c = data[foff + i] ^ key[i % klen]
                    if not (0x20 <= c < 0x7F):
                        break
                    out.append(c)
                    if c == ord("}"):
                        print("key :", key.decode())
                        print("flag:", out.decode())
                        return
    print("no solution found", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
