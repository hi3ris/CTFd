#!/usr/bin/env python3
# gen.py - DEV-ONLY. Assembles the SynthVM bytecode "checker" program and writes
# src/program.h (an embedded byte array compiled into ./synthvm).
#
# This file is NOT distributed to players. It is the single source of truth for:
#   - the invented instruction encoding (custom LSB-continuation varint),
#   - the runtime opcode remap (keyed Fisher-Yates over a xorshift32 PRNG),
#   - the invented S-box,
#   - the ~6000-instruction unrolled keygen check.
#
# The compiled interpreter (src/vm.c) MUST use the identical OP_SEED / SBOX_SEED
# and the identical varint/rotate/sbox semantics, or the produced program will
# not run. `make verify` checks the whole thing end to end.

import sys

# ---------------------------------------------------------------------------
# Tunables that also live (as literal constants) in vm.c. Keep in sync.
# ---------------------------------------------------------------------------
OP_SEED   = 0x1F3D5B79      # seeds the opcode dispatch permutation
SBOX_SEED = 0xC0FFEE42      # seeds the 8-bit S-box permutation

# Keygen parameters (baked into the program as instruction immediates; a player
# recovers them from the disassembly, not from this file).
K1  = 0x1B
K2  = 0x71
R   = 17                    # number of mixing rounds (unrolled)
def rot_of(r):  return (r * 3 + 1) & 7
def iv_of(r):   return (r * 0x9E + 0x3D) & 0xFF

BUF   = 0x0100              # input buffer base inside data RAM (mem[])
EOF_SENTINEL = 0x100        # IN returns this dword on end-of-input

# The flag == the accepted input. It is NEVER emitted into the artifact in
# plaintext; only its S-box/rotate/add image T[] is stored as CMPI immediates.
FLAG = "NCTF{synthvm_d1sp4tch_rem4pped_at_runtime}"
FLAGB = FLAG.encode()
L = len(FLAGB)

# Decoy: a plausible alternate checker living in DEAD (unreachable) code. Someone
# who lifts it and inverts gets FAKE, which the real program rejects. Refutable
# in minutes from the control-flow graph (nothing jumps to it).
FAKE = ("NCTF{dead_c0de_is_a_trap_keep_tracing!!}" + "~" * L)[:L].encode()
DECOY_XOR = 0x5A

# ---------------------------------------------------------------------------
# xorshift32 + keyed Fisher-Yates permutation (mirrors vm.c exactly)
# ---------------------------------------------------------------------------
def xs32(x):
    x &= 0xFFFFFFFF
    x ^= (x << 13) & 0xFFFFFFFF
    x ^= (x >> 17)
    x ^= (x << 5) & 0xFFFFFFFF
    return x & 0xFFFFFFFF

def permutation(seed, n=256):
    arr = list(range(n))
    st = seed & 0xFFFFFFFF
    for i in range(n - 1, 0, -1):
        st = xs32(st)
        j = st % (i + 1)
        arr[i], arr[j] = arr[j], arr[i]
    return arr

# opmap[raw_byte] = internal_op. The assembler needs the inverse: to emit an
# internal op it writes the raw byte whose opmap entry equals that op.
OPMAP = permutation(OP_SEED)
INV_OPMAP = [0] * 256
for raw, internal in enumerate(OPMAP):
    INV_OPMAP[internal] = raw

# Invented S-box (a full 8-bit bijection) and its inverse.
SBOX = permutation(SBOX_SEED)
ISBOX = [0] * 256
for i, v in enumerate(SBOX):
    ISBOX[v] = i

def rol8(x, n):
    x &= 0xFF; n &= 7
    if n == 0: return x
    return ((x << n) | (x >> (8 - n))) & 0xFF

def ror8(x, n):
    x &= 0xFF; n &= 7
    if n == 0: return x
    return ((x >> n) | (x << (8 - n))) & 0xFF

# ---------------------------------------------------------------------------
# Custom varint: 7 payload bits in the HIGH bits of each byte; the LOW bit is
# the continuation flag (1 = more bytes follow). Little-endian payload order.
# This is deliberately NOT LEB128 (whose MSB is the continuation flag).
# ---------------------------------------------------------------------------
def venc(v):
    out = bytearray()
    while True:
        b = (v & 0x7F) << 1
        v >>= 7
        if v:
            out.append(b | 1)
        else:
            out.append(b)
            break
    return bytes(out)

def vencw(v, w):
    # Fixed-width (w bytes) encoding: first w-1 bytes carry continuation=1,
    # the final byte carries continuation=0. Decoder stops at the 0 bit.
    out = bytearray()
    for k in range(w):
        b = (v & 0x7F) << 1
        v >>= 7
        if k != w - 1:
            b |= 1
        out.append(b)
    return bytes(out)

BR_WIDTH = 3   # branch targets: fixed 3-byte varint (covers 21 bits >> code size)

# ---------------------------------------------------------------------------
# Opcode table (internal index == position). vm.c uses the same numbering.
# ---------------------------------------------------------------------------
NAMES = [
    "NOP","HALT","MOV","MOVI","ADD","SUB","MUL","XOR","AND","OR","SHL","SHR",
    "ROL","ROR","NOT","NEG","ADDI","SUBI","XORI","ANDI","ORI","MULI","SHLI",
    "SHRI","ROLI","RORI","CMP","CMPI","TEST","LDB","LDW","LDD","STB","STW",
    "STD","LEA","PUSH","POP","JMP","JZ","JNZ","JC","JNC","JG","JL","JGE","JLE",
    "JA","JB","CALL","RET","IN","OUT","RND","SBOX","ISBOX","ROL8","ROR8",
    "POPCNT","CLZ","BSWAP","REVB","SEXTB","MULH","DIV","MOD","MIN","MAX","SWP",
    "INC","DEC","CLR","SETZ","NAND","NOR","ADC","SBB","MIX","ENTER","LEAVE",
]
assert len(NAMES) == 80, len(NAMES)
OP = {name: i for i, name in enumerate(NAMES)}

FORMAT = {}
for n in ["NOP","HALT","RET","LEAVE"]:                       FORMAT[n]="NONE"
for n in ["NOT","NEG","PUSH","POP","IN","OUT","RND","BSWAP",
          "REVB","SEXTB","INC","DEC","CLR","SETZ"]:           FORMAT[n]="R1"
for n in ["MOV","ADD","SUB","MUL","XOR","AND","OR","SHL","SHR","ROL","ROR",
          "CMP","TEST","SBOX","ISBOX","POPCNT","CLZ","MULH","DIV","MOD","MIN",
          "MAX","SWP","NAND","NOR","ADC","SBB","MIX"]:        FORMAT[n]="R2"
for n in ["MOVI","ADDI","SUBI","XORI","ANDI","ORI","MULI","SHLI","SHRI","ROLI",
          "RORI","CMPI","ROL8","ROR8"]:                       FORMAT[n]="RI"
for n in ["LDB","LDW","LDD","STB","STW","STD","LEA"]:         FORMAT[n]="RM"
for n in ["JMP","JZ","JNZ","JC","JNC","JG","JL","JGE","JLE",
          "JA","JB","CALL"]:                                  FORMAT[n]="BR"
for n in ["ENTER"]:                                           FORMAT[n]="IMM"
assert all(n in FORMAT for n in NAMES), [n for n in NAMES if n not in FORMAT]

# ---------------------------------------------------------------------------
# Tiny two-pass assembler with labels.
# ---------------------------------------------------------------------------
class Asm:
    def __init__(self):
        self.items = []          # ('L', name) or ('I', mnem, args)
    def label(self, name):
        self.items.append(('L', name))
    def ins(self, mnem, **kw):
        self.items.append(('I', mnem, kw))

    def _size(self, mnem, kw):
        f = FORMAT[mnem]
        if f == "NONE": return 1
        if f == "R1":   return 2
        if f == "R2":   return 2
        if f == "RI":   return 2 + len(venc(kw["imm"]))
        if f == "RM":   return 2 + len(venc(kw["off"]))
        if f == "BR":   return 1 + BR_WIDTH
        if f == "IMM":  return 1 + len(venc(kw["imm"]))
        raise ValueError(f)

    def assemble(self):
        # pass 1: addresses (all sizes are known without resolving labels,
        # because branch targets use a fixed width)
        addr = 0
        labels = {}
        for it in self.items:
            if it[0] == 'L':
                labels[it[1]] = addr
            else:
                addr += self._size(it[1], it[2])
        # pass 2: emit
        out = bytearray()
        for it in self.items:
            if it[0] == 'L':
                continue
            _, mnem, kw = it
            raw = INV_OPMAP[OP[mnem]]
            f = FORMAT[mnem]
            out.append(raw)
            if f == "NONE":
                pass
            elif f == "R1":
                out.append((kw["d"] & 0xF) << 4)
            elif f == "R2":
                out.append(((kw["d"] & 0xF) << 4) | (kw["s"] & 0xF))
            elif f == "RI":
                out.append((kw["d"] & 0xF) << 4)
                out += venc(kw["imm"])
            elif f == "RM":
                out.append(((kw["d"] & 0xF) << 4) | (kw["base"] & 0xF))
                out += venc(kw["off"])
            elif f == "BR":
                out += vencw(labels[kw["target"]], BR_WIDTH)
            elif f == "IMM":
                out += venc(kw["imm"])
        return bytes(out), labels

# ---------------------------------------------------------------------------
# Forward keygen transform (defines T[]).  buf is a bytearray of length L.
# ---------------------------------------------------------------------------
def forward(bufin):
    a = bytearray(bufin)
    for r in range(R):
        rot = rot_of(r)
        carry = iv_of(r)
        for i in range(L):
            t = a[i]
            t = (t + carry) & 0xFF
            t = SBOX[t]
            t = rol8(t, rot)
            t ^= (i * K1 + r * K2) & 0xFF
            a[i] = t
            carry = t
    return a

def invert(target):
    a = bytearray(target)
    for r in reversed(range(R)):
        rot = rot_of(r)
        O = bytearray(a)               # this round's outputs
        for i in range(L):
            out = O[i]
            t = out ^ ((i * K1 + r * K2) & 0xFF)
            t = ror8(t, rot)
            t = ISBOX[t]
            carry = iv_of(r) if i == 0 else O[i - 1]
            a[i] = (t - carry) & 0xFF
    return a

T = forward(FLAGB)
DECOY_T = bytes((FAKE[i] ^ DECOY_XOR) & 0xFF for i in range(L))
# sanity: inversion round-trips
assert invert(T) == FLAGB, "invert(forward(flag)) != flag"

# ---------------------------------------------------------------------------
# Build the program.
#   r1  = working byte t
#   r2  = input byte scratch
#   r3  = output scratch
#   r6  = carry
#   r14 = BUF base
# ---------------------------------------------------------------------------
a = Asm()

# --- setup ---
a.ins("MOVI", d=14, imm=BUF)

# --- read exactly L bytes into BUF (unrolled) ---
for i in range(L):
    a.ins("IN",   d=2)
    a.ins("CMPI", d=2, imm=EOF_SENTINEL)
    a.ins("JZ",   target="reject")
    a.ins("ANDI", d=2, imm=0xFF)
    a.ins("STB",  d=2, base=14, off=i)

# --- R mixing rounds (unrolled) ---
for r in range(R):
    rot = rot_of(r)
    a.ins("MOVI", d=6, imm=iv_of(r))
    for i in range(L):
        c = (i * K1 + r * K2) & 0xFF
        a.ins("LDB",  d=1, base=14, off=i)
        a.ins("ADD",  d=1, s=6)
        a.ins("ANDI", d=1, imm=0xFF)
        a.ins("SBOX", d=1, s=1)
        a.ins("ROL8", d=1, imm=rot)
        a.ins("XORI", d=1, imm=c)
        a.ins("STB",  d=1, base=14, off=i)
        a.ins("MOV",  d=6, s=1)

# --- compare BUF against T[] ---
for i in range(L):
    a.ins("LDB",  d=1, base=14, off=i)
    a.ins("CMPI", d=1, imm=T[i])
    a.ins("JNZ",  target="reject")

# --- success ---
for ch in b"Access granted\n":
    a.ins("MOVI", d=3, imm=ch)
    a.ins("OUT",  d=3)
a.ins("HALT")

# --- reject ---
a.label("reject")
for ch in b"Denied\n":
    a.ins("MOVI", d=3, imm=ch)
    a.ins("OUT",  d=3)
a.ins("HALT")

# --- DEAD decoy checker (never reached: the two HALTs above end all live paths,
#     and nothing branches to 'decoy') ---
a.label("decoy")
for i in range(L):
    a.ins("LDB",  d=1, base=14, off=i)
    a.ins("XORI", d=1, imm=DECOY_XOR)
    a.ins("CMPI", d=1, imm=DECOY_T[i])
    a.ins("JNZ",  target="decoy_bad")
for ch in b"Access granted\n":
    a.ins("MOVI", d=3, imm=ch)
    a.ins("OUT",  d=3)
a.ins("HALT")
a.label("decoy_bad")
a.ins("HALT")

PROG, labels = a.assemble()
NUM_INSNS = sum(1 for it in a.items if it[0] == 'I')

def write_header(path):
    lines = []
    lines.append("/* AUTO-GENERATED by src/gen.py - do not edit. Not shipped to players. */")
    lines.append("#ifndef SYNTHVM_PROGRAM_H")
    lines.append("#define SYNTHVM_PROGRAM_H")
    lines.append("")
    lines.append(f"#define PROG_LEN {len(PROG)}u")
    lines.append("static const unsigned char PROG[PROG_LEN] = {")
    for k in range(0, len(PROG), 16):
        chunk = PROG[k:k + 16]
        lines.append("    " + "".join(f"0x{b:02x}," for b in chunk))
    lines.append("};")
    lines.append("")
    lines.append("#endif")
    lines.append("")
    with open(path, "w") as fh:
        fh.write("\n".join(lines))

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "program.h"
    write_header(out)
    print(f"[gen] flag len       : {L}")
    print(f"[gen] rounds R        : {R}")
    print(f"[gen] instructions    : {NUM_INSNS}")
    print(f"[gen] PROG bytes      : {len(PROG)}")
    print(f"[gen] wrote           : {out}")
    # never print FLAG in build logs
