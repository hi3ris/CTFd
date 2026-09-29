#!/usr/bin/env python3
"""Assemble program.txt for stack-vm.

The output is a program for a tiny stack machine with a flat memory. A data
section holds one obfuscated byte per flag character; the code is a LOOP that,
for each cell, computes EMIT((data[i] * K + C) mod 256) so the raw data bytes
are NOT the flag. Running the VM prints the flag.

Memory layout: mem[0] = loop index i, mem[1] = remaining count,
data lives at addresses DATA_BASE .. DATA_BASE + L - 1.

STORE semantics: pops ADDR, then VAL  (so push VAL, push ADDR, STORE).
LOAD  semantics: pops ADDR, pushes mem[ADDR].
Binary ops pop B then A and push (A op B).
"""

import os

FLAG = "NCTF{tiny_stack_vm_prints_this_flag}"
K = 37  # odd => invertible mod 256
C = 91
DATA_BASE = 1000


def inv_mod_256(a):
    for x in range(256):
        if (a * x) % 256 == 1:
            return x
    raise ValueError("not invertible")


def main():
    kinv = inv_mod_256(K)
    data = [((ord(ch) - C) * kinv) % 256 for ch in FLAG]
    L = len(FLAG)

    lines = []
    # mem[1] = L   (remaining)
    lines += [f"PUSH {L}", "PUSH 1", "STORE"]
    # mem[0] = 0   (index)
    lines += ["PUSH 0", "PUSH 0", "STORE"]
    lines += ["loop:"]
    # if remaining == 0 -> end
    lines += ["PUSH 1", "LOAD", "JZ end"]
    # value = mem[DATA_BASE + i]
    lines += [f"PUSH {DATA_BASE}", "PUSH 0", "LOAD", "ADD", "LOAD"]
    # value = value * K + C ; value %= 256 ; emit
    lines += [f"PUSH {K}", "MUL", f"PUSH {C}", "ADD", "PUSH 256", "MOD", "EMIT"]
    # i = i + 1
    lines += ["PUSH 0", "LOAD", "PUSH 1", "ADD", "PUSH 0", "STORE"]
    # remaining = remaining - 1
    lines += ["PUSH 1", "LOAD", "PUSH 1", "SUB", "PUSH 1", "STORE"]
    lines += ["JMP loop", "end:", "HALT"]
    # data directive: base then values
    lines += [".data " + str(DATA_BASE) + " " + " ".join(str(d) for d in data)]

    out = os.path.join(os.path.dirname(__file__), "..", "program.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("wrote", os.path.relpath(out), "instructions:", len(lines))


if __name__ == "__main__":
    main()
