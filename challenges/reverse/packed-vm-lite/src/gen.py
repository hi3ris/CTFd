#!/usr/bin/env python3
"""
Developer-only generator/assembler for the 'packed-vm-lite' reverse challenge.

NOT shipped to players. Players receive only the compiled ELF 'vmcheck' plus
the description. This script:

  1. defines a tiny custom bytecode ISA (a register+stack VM, ~30 opcodes),
  2. assembles a serial-validation program with a real loop and jumps,
  3. computes the embedded KEY[] and TARGET[] tables from the intended serial,
  4. emits program.h (arrays) which vm.c #includes.

Design of the validation
-------------------------
The intended inner serial (24 bytes) is transformed byte-by-byte inside the VM
and each result is compared to TARGET[i]. The transform per index i (0-based):

    amt   = (i*3 + 1) & 7                 # variable rotate amount
    t     = rotl8(serial[i], amt)
    t     = t ^ KEY[i]
    t     = (t + prev) & 0xFF             # feedback from previous *plaintext*
    check   t == TARGET[i]
    prev  = serial[i]                     # NB: prev is the raw byte, not t

with prev seeded to 0x5A. The chaining on the raw plaintext byte makes the
recovery strictly sequential (byte i needs byte i-1), and the variable rotate +
per-index key mean you must read the opcode semantics correctly, not guess.

The flag is NOT stored anywhere in the binary (not even XOR'd). On success the
program simply prints  CTF{ + <the serial you typed> + }.  So the only way to
learn the flag is to produce the serial that validates.
"""

# ---- intended serial: flag = CTF{ + SERIAL + } ------------------------------
SERIAL = b"vm_bytec0de_1s_n0t_h4rd!"          # exactly 24 bytes
assert len(SERIAL) == 24, len(SERIAL)

# Fixed per-index key table (looks random; is just a constant table).
KEY = [((i * 37 + 0x9E) ^ (i << 1) ^ 0xC3) & 0xFF for i in range(24)]

SEED = 0x5A

def rotl8(v, n):
    n &= 7
    return ((v << n) | (v >> (8 - n))) & 0xFF

def build_target():
    prev = SEED
    tgt = []
    for i in range(24):
        c = SERIAL[i]
        amt = (i * 3 + 1) & 7
        t = rotl8(c, amt)
        t ^= KEY[i]
        t = (t + prev) & 0xFF
        tgt.append(t)
        prev = c
    return tgt

TARGET = build_target()

# ---- ISA --------------------------------------------------------------------
# Keep in lockstep with the switch() in vm.c. Opcodes are 1 byte; some take a
# 1-byte immediate operand that follows.
OPS = {
    "NOP":    (0x00, 0),
    "PUSH":   (0x01, 1),   # push imm8
    "POP":    (0x02, 0),
    "DUP":    (0x03, 0),
    "SWAP":   (0x04, 0),
    "LDR":    (0x05, 1),   # push regs[imm]
    "STR":    (0x06, 1),   # pop -> regs[imm]
    "INC":    (0x07, 1),   # regs[imm]++
    "DEC":    (0x08, 1),   # regs[imm]--
    "LOADR":  (0x09, 0),   # pop idx -> push input[idx]
    "LOADK":  (0x0A, 0),   # pop idx -> push KEY[idx]
    "LOADT":  (0x0B, 0),   # pop idx -> push TARGET[idx]
    "ADD":    (0x0C, 0),
    "SUB":    (0x0D, 0),   # pop a,b -> push (b-a)&0xff
    "XOR":    (0x0E, 0),
    "AND":    (0x0F, 0),
    "OR":     (0x10, 0),
    "MUL":    (0x11, 0),
    "ADDI":   (0x12, 1),
    "XORI":   (0x13, 1),
    "MULI":   (0x14, 1),
    "ANDI":   (0x15, 1),
    "ROLV":   (0x16, 0),   # pop amt, pop val -> push rotl8(val, amt&7)
    "RORV":   (0x17, 0),   # decoy: present, unused by the program
    "NOT":    (0x18, 0),   # decoy: present, unused
    "CMPEQ":  (0x19, 0),   # pop a,b -> push (a==b)?1:0
    "LEN":    (0x1A, 0),   # push input length
    "CHKLEN": (0x1B, 1),   # if len!=imm set regs[3]=1 (fail)
    "JMP":    (0x1C, 1),   # absolute jump to imm (program offset)
    "JZ":     (0x1D, 1),   # pop; if ==0 jump imm
    "JNZ":    (0x1E, 1),   # pop; if !=0 jump imm
    "HALT":   (0x1F, 0),
}

class Asm:
    def __init__(self):
        self.code = []          # list of (kind, ...)
        self.labels = {}
    def emit(self, op, arg=None):
        self.code.append(("op", op, arg))
    def label(self, name):
        self.code.append(("label", name))
    def assemble(self):
        # pass 1: compute offsets
        off = 0
        offs = []
        for item in self.code:
            if item[0] == "label":
                self.labels[item[1]] = off
                offs.append(None)
            else:
                _, op, arg = item
                offs.append(off)
                sz = 1 + OPS[op][1]
                off += sz
        total = off
        # pass 2: emit bytes, resolving label args
        out = bytearray()
        for item in self.code:
            if item[0] == "label":
                continue
            _, op, arg = item
            code, nargs = OPS[op]
            out.append(code)
            if nargs:
                if isinstance(arg, str):        # label reference
                    arg = self.labels[arg]
                out.append(arg & 0xFF)
        assert len(out) == total
        return bytes(out)

def program():
    a = Asm()
    # regs: r0=index, r1=prev(feedback), r3=fail, r5=saved current byte,
    #       r6=success flag (read by C)
    a.emit("CHKLEN", 24)
    a.emit("PUSH", SEED); a.emit("STR", 1)     # prev = 0x5A
    a.emit("PUSH", 0);    a.emit("STR", 0)     # i = 0
    a.emit("PUSH", 0);    a.emit("STR", 3)     # fail = 0

    a.label("LOOP")
    a.emit("LDR", 0); a.emit("PUSH", 24); a.emit("CMPEQ")  # i==24 ?
    a.emit("JNZ", "END")                                    # if equal -> done

    # c = input[i]; save copy in r5
    a.emit("LDR", 0); a.emit("LOADR")          # stack: c
    a.emit("DUP");    a.emit("STR", 5)          # r5 = c ; stack: c

    # amt = (i*3 + 1) & 7
    a.emit("LDR", 0); a.emit("MULI", 3); a.emit("ADDI", 1); a.emit("ANDI", 7)
    a.emit("ROLV")                              # stack: rotl8(c, amt)

    # ^ KEY[i]
    a.emit("LDR", 0); a.emit("LOADK"); a.emit("XOR")

    # + prev
    a.emit("LDR", 1); a.emit("ADD")             # stack: t

    # == TARGET[i]  -> eq
    a.emit("LDR", 0); a.emit("LOADT"); a.emit("CMPEQ")   # stack: eq

    # mismatch = (eq == 0)
    a.emit("PUSH", 0); a.emit("CMPEQ")          # stack: mismatch
    a.emit("LDR", 3); a.emit("OR"); a.emit("STR", 3)     # fail |= mismatch

    # prev = c (r5)
    a.emit("LDR", 5); a.emit("STR", 1)

    a.emit("INC", 0)
    a.emit("JMP", "LOOP")

    a.label("END")
    a.emit("LDR", 3); a.emit("JNZ", "FAIL")     # any fail -> not success
    a.emit("PUSH", 1); a.emit("STR", 6); a.emit("HALT")   # success
    a.label("FAIL")
    a.emit("PUSH", 0); a.emit("STR", 6); a.emit("HALT")

    return a.assemble()

def carr(name, data, typ="unsigned char"):
    body = ", ".join("0x%02x" % b for b in data)
    return "static const %s %s[%d] = { %s };" % (typ, name, len(data), body)

def main():
    prog = program()
    hdr = []
    hdr.append("/* program.h -- auto-generated by src/gen.py; do not hand-edit. */")
    hdr.append("/* Bytecode + tables for the packed-vm-lite validator VM.       */")
    hdr.append("")
    hdr.append("#define PROG_LEN %d" % len(prog))
    hdr.append("#define SERIAL_LEN 24")
    hdr.append("")
    hdr.append(carr("PROG", prog))
    hdr.append(carr("VMKEY", KEY))
    hdr.append(carr("VMTARGET", TARGET))
    hdr.append("")
    text = "\n".join(hdr) + "\n"
    with open("program.h", "w") as f:
        f.write(text)
    print("wrote program.h (PROG_LEN=%d)" % len(prog))
    print("serial:", SERIAL.decode())
    print("flag:  CTF{%s}" % SERIAL.decode())

if __name__ == "__main__":
    main()
