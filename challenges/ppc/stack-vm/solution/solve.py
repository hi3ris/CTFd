#!/usr/bin/env python3
"""Interpret program.txt on the tiny stack machine; its output is the flag.

ISA (one instruction per line, labels end with ':'):
  PUSH n   push integer n
  POP      discard top
  LOAD     addr = pop; push mem[addr]
  STORE    addr = pop; val = pop; mem[addr] = val
  ADD/SUB/MUL/MOD   b = pop; a = pop; push (a op b)
  DUP      push top again
  EMIT     v = pop; output chr(v & 0xFF)
  JMP L    jump to label L
  JZ  L    c = pop; if c == 0 jump to L
  HALT     stop
  .data BASE v0 v1 ...   preload mem[BASE + i] = vi
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROGRAM = os.path.join(HERE, "..", "program.txt")


def run(text):
    code = []
    labels = {}
    mem = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(".data"):
            parts = line.split()
            base = int(parts[1])
            for i, v in enumerate(parts[2:]):
                mem[base + i] = int(v)
            continue
        if line.endswith(":"):
            labels[line[:-1]] = len(code)
            continue
        code.append(line.split())

    stack = []
    out = []
    pc = 0
    while pc < len(code):
        ins = code[pc]
        op = ins[0]
        if op == "PUSH":
            stack.append(int(ins[1]))
        elif op == "POP":
            stack.pop()
        elif op == "LOAD":
            addr = stack.pop()
            stack.append(mem.get(addr, 0))
        elif op == "STORE":
            addr = stack.pop()
            val = stack.pop()
            mem[addr] = val
        elif op == "ADD":
            b = stack.pop()
            a = stack.pop()
            stack.append(a + b)
        elif op == "SUB":
            b = stack.pop()
            a = stack.pop()
            stack.append(a - b)
        elif op == "MUL":
            b = stack.pop()
            a = stack.pop()
            stack.append(a * b)
        elif op == "MOD":
            b = stack.pop()
            a = stack.pop()
            stack.append(a % b)
        elif op == "DUP":
            stack.append(stack[-1])
        elif op == "EMIT":
            out.append(chr(stack.pop() & 0xFF))
        elif op == "JMP":
            pc = labels[ins[1]]
            continue
        elif op == "JZ":
            if stack.pop() == 0:
                pc = labels[ins[1]]
                continue
        elif op == "HALT":
            break
        else:
            raise ValueError("unknown op " + op)
        pc += 1
    return "".join(out)


def main():
    with open(PROGRAM, encoding="utf-8") as fh:
        print(run(fh.read()))


if __name__ == "__main__":
    main()
