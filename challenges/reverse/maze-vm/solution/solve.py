#!/usr/bin/env python3
"""
Reference solver for reverse/maze-vm.

Intended (static) path, done programmatically:

  1. Locate the embedded blob in the ELF by its magic "MZVMv1", and read the
     rolling-key parameters, the obfuscated bytecode, and the target image.
  2. De-obfuscate the bytecode with the same rolling keystream the binary uses
     at startup.
  3. Re-implement the maze-vm and DISASSEMBLE / interpret the recovered program
     (no transform constants are hardcoded here -- the interpreter is driven by
     the lifted bytecode).
  4. Use the interpreter as a white-box oracle. Because the round arithmetic is
     per-byte and the only cross-byte step is a pure permutation, every output
     byte depends on exactly one input byte, so each input byte is recovered
     independently by a 256-value scan (16 * 256 evaluations).
  5. The recovered input IS the inner flag text: feed it to the real binary and
     confirm it prints NCTF{<input>}.

Usage:  python3 solve.py ../chall
"""
import subprocess
import sys

# opcodes (read out of the disassembly; listed here for the interpreter)
NOP, HALT = 0x10, 0x11
PUSHI, LDIN, LDST, STST = 0x12, 0x13, 0x14, 0x15
POP, DUP, SWAP = 0x16, 0x17, 0x18
ADD, SUB, XOR, AND, OR = 0x19, 0x1A, 0x1B, 0x1C, 0x1D
MULMOD = 0x1E
ROL, ROR = 0x1F, 0x20
PERM = 0x21
CMP = 0x22
JMP = 0x23

# operand widths for linear disassembly (0 = no operand byte, PLEN handled inline)
IMM1 = {PUSHI, LDIN, LDST, STST, ROL, ROR, JMP}


def extract_blob(path):
    data = open(path, "rb").read()
    off = data.find(b"MZVMv1\x00\x00")
    if off < 0:
        raise SystemExit("blob magic not found")
    p = off + 8
    xor_seed, xor_mul, plen = data[p], data[p + 1], data[p + 2]
    prog_len = data[p + 3] | (data[p + 4] << 8)
    obf = data[p + 5:p + 5 + prog_len]
    target = data[p + 5 + prog_len:p + 5 + prog_len + plen]
    return xor_seed, xor_mul, plen, obf, list(target)


def deobfuscate(obf, seed, mul):
    key = seed
    prog = []
    for o in obf:
        prog.append(o ^ key)
        key = (key * mul + o) & 0xFF
    return prog


def disassemble(prog, plen):
    """Linear disassembly -- proves the stream decodes as valid instructions."""
    pc, out = 0, []
    while pc < len(prog):
        op = prog[pc]; pc += 1
        if op == PERM:
            out.append((PERM, list(prog[pc:pc + plen]))); pc += plen
        elif op in IMM1:
            out.append((op, prog[pc])); pc += 1
        else:
            out.append((op, None))
        if op == HALT:
            break
    return out


def rol8(x, n): return ((x << n) | (x >> (8 - n))) & 0xFF
def ror8(x, n): return ((x >> n) | (x << (8 - n))) & 0xFF


def run_vm(prog, inp, plen):
    """Interpret the lifted bytecode; return the computed state array st[]."""
    st = [0] * 64
    stk, pc = [], 0
    while pc < len(prog):
        op = prog[pc]; pc += 1
        if op == HALT or op == 0x00:
            break
        elif op == NOP:      pass
        elif op == PUSHI:    stk.append(prog[pc]); pc += 1
        elif op == LDIN:     stk.append(inp[prog[pc]]); pc += 1
        elif op == LDST:     stk.append(st[prog[pc]]); pc += 1
        elif op == STST:     st[prog[pc]] = stk.pop(); pc += 1
        elif op == POP:      stk.pop()
        elif op == DUP:      stk.append(stk[-1])
        elif op == SWAP:     stk[-1], stk[-2] = stk[-2], stk[-1]
        elif op == ADD:      b = stk.pop(); stk[-1] = (stk[-1] + b) & 0xFF
        elif op == SUB:      b = stk.pop(); stk[-1] = (stk[-1] - b) & 0xFF
        elif op == XOR:      b = stk.pop(); stk[-1] ^= b
        elif op == AND:      b = stk.pop(); stk[-1] &= b
        elif op == OR:       b = stk.pop(); stk[-1] |= b
        elif op == MULMOD:   b = stk.pop(); stk[-1] = (stk[-1] * b) & 0xFF
        elif op == ROL:      c = prog[pc] & 7; stk[-1] = rol8(stk[-1], c); pc += 1
        elif op == ROR:      c = prog[pc] & 7; stk[-1] = ror8(stk[-1], c); pc += 1
        elif op == PERM:
            tmp = [st[prog[pc + i]] for i in range(plen)]
            st[:plen] = tmp; pc += plen
        elif op == CMP:      stk.pop(); stk.pop()      # comparison, no state change
        elif op == JMP:      pc = prog[pc]
        else:                raise SystemExit("bad opcode 0x%02x" % op)
    return st[:plen]


def recover_input(prog, plen, target):
    """Each output byte depends on one input byte -> scan each position."""
    inp = [0] * plen
    for i in range(plen):
        best_v, best_score = 0, -1
        for v in range(256):
            inp[i] = v
            st = run_vm(prog, inp, plen)
            score = sum(1 for k in range(plen) if st[k] == target[k])
            if score > best_score:
                best_score, best_v = score, v
        inp[i] = best_v
    return inp


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py <chall-binary>")
    binpath = sys.argv[1]
    seed, mul, plen, obf, target = extract_blob(binpath)
    prog = deobfuscate(obf, seed, mul)
    dis = disassemble(prog, plen)
    print("[*] blob: plen=%d prog_len=%d seed=0x%02x mul=0x%02x  (%d instrs)"
          % (plen, len(prog), seed, mul, len(dis)))

    inp = recover_input(prog, plen, target)
    st = run_vm(prog, inp, plen)
    assert st == target, "recovered input does not reproduce target"
    inp_bytes = bytes(inp)
    print("[*] recovered input : %r" % inp_bytes)

    # the recovered input IS the inner flag text; confirm against the real binary
    out = subprocess.run([binpath], input=inp_bytes + b"\n",
                         capture_output=True).stdout.decode().strip()
    print("[*] binary output   : %s" % out)
    expected = "NCTF{" + inp_bytes.decode() + "}"
    assert out == expected, "binary did not print the expected flag"
    print("[+] FLAG: %s" % out)


if __name__ == "__main__":
    main()
