#!/usr/bin/env python3
"""Emit cipher.txt for brainfuck-cascade.

We compile the flag into a Brainfuck program (one cell, delta-encoded, print
each byte), then base85-encode the program source. The shipped artifact is only
the base85 blob, so neither the flag nor the word "brainfuck" appears in it.
"""

import base64
import os

FLAG = "NCTF{b85_then_brainfuck_all_the_way_down}"


def compile_bf(text: str) -> str:
    out = []
    cur = 0
    for ch in text:
        target = ord(ch)
        delta = target - cur
        out.append(("+" if delta > 0 else "-") * abs(delta))
        out.append(".")
        cur = target
    return "".join(out)


def main() -> None:
    program = compile_bf(FLAG)
    blob = base64.b85encode(program.encode("ascii")).decode("ascii")
    out = os.path.join(os.path.dirname(__file__), "..", "cipher.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(blob + "\n")
    print("wrote", os.path.relpath(out), "bf_len:", len(program))


if __name__ == "__main__":
    main()
