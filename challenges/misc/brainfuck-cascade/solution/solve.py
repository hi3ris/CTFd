#!/usr/bin/env python3
"""base85-decode cipher.txt to a Brainfuck program, run it, print the flag."""

import base64
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CIPHER = os.path.join(HERE, "..", "cipher.txt")


def run_bf(src: str) -> str:
    tape = [0] * 30000
    ptr = 0
    out = []
    # Precompute bracket matches.
    jumps = {}
    stack = []
    for i, c in enumerate(src):
        if c == "[":
            stack.append(i)
        elif c == "]":
            j = stack.pop()
            jumps[i] = j
            jumps[j] = i

    i = 0
    while i < len(src):
        c = src[i]
        if c == ">":
            ptr += 1
        elif c == "<":
            ptr -= 1
        elif c == "+":
            tape[ptr] = (tape[ptr] + 1) & 0xFF
        elif c == "-":
            tape[ptr] = (tape[ptr] - 1) & 0xFF
        elif c == ".":
            out.append(chr(tape[ptr]))
        elif c == "[" and tape[ptr] == 0:
            i = jumps[i]
        elif c == "]" and tape[ptr] != 0:
            i = jumps[i]
        i += 1
    return "".join(out)


def main() -> None:
    with open(CIPHER, encoding="utf-8") as fh:
        blob = fh.read().strip()
    program = base64.b85decode(blob).decode("ascii")
    print(run_bf(program))


if __name__ == "__main__":
    main()
