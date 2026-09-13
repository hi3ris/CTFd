#!/usr/bin/env python3
"""
Solver for reverse/synthvm.

This is the INTENDED path, done programmatically:

  1. Recover the two seeds from the binary's init routine (OP_SEED for the
     opcode dispatch permutation, SBOX_SEED for the S-box) and rebuild both
     permutations with the same keyed Fisher-Yates over xorshift32.
  2. Locate the embedded bytecode (PROG) inside the ELF by its first
     instruction, then LINEARLY DISASSEMBLE it using the recovered opcode map
     and the custom LSB-continuation varint.
  3. Read the checker parameters straight out of the disassembly: the per-round
     carry seed (MOVI r6), the per-round byte rotate (ROL8), the per-(round,
     index) XOR constants (XORI r1), and the comparison target T[] (CMPI r1).
  4. Invert the round function to recover the accepted input == the flag.
  5. Verify by feeding the recovered flag back into the real binary.

Nothing about the flag string is hardcoded here; everything is lifted.

Usage:
    python3 solve.py ../synthvm
"""
import subprocess
import sys

# --- constants a player reads out of the binary's init_dispatch / permute ---
OP_SEED   = 0x1F3D5B79
SBOX_SEED = 0xC0FFEE42

NAMES = [
    "NOP","HALT","MOV","MOVI","ADD","SUB","MUL","XOR","AND","OR","SHL","SHR",
    "ROL","ROR","NOT","NEG","ADDI","SUBI","XORI","ANDI","ORI","MULI","SHLI",
    "SHRI","ROLI","RORI","CMP","CMPI","TEST","LDB","LDW","LDD","STB","STW",
    "STD","LEA","PUSH","POP","JMP","JZ","JNZ","JC","JNC","JG","JL","JGE","JLE",
    "JA","JB","CALL","RET","IN","OUT","RND","SBOX","ISBOX","ROL8","ROR8",
    "POPCNT","CLZ","BSWAP","REVB","SEXTB","MULH","DIV","MOD","MIN","MAX","SWP",
    "INC","DEC","CLR","SETZ","NAND","NOR","ADC","SBB","MIX","ENTER","LEAVE",
]
OP = {n: i for i, n in enumerate(NAMES)}
FMT = {}
for n in ["NOP","HALT","RET","LEAVE"]: FMT[n]="NONE"
for n in ["NOT","NEG","PUSH","POP","IN","OUT","RND","BSWAP","REVB","SEXTB",
          "INC","DEC","CLR","SETZ"]: FMT[n]="R1"
for n in ["MOV","ADD","SUB","MUL","XOR","AND","OR","SHL","SHR","ROL","ROR",
          "CMP","TEST","SBOX","ISBOX","POPCNT","CLZ","MULH","DIV","MOD","MIN",
          "MAX","SWP","NAND","NOR","ADC","SBB","MIX"]: FMT[n]="R2"
for n in ["MOVI","ADDI","SUBI","XORI","ANDI","ORI","MULI","SHLI","SHRI","ROLI",
          "RORI","CMPI","ROL8","ROR8"]: FMT[n]="RI"
for n in ["LDB","LDW","LDD","STB","STW","STD","LEA"]: FMT[n]="RM"
for n in ["JMP","JZ","JNZ","JC","JNC","JG","JL","JGE","JLE","JA","JB","CALL"]:
    FMT[n]="BR"
FMT["ENTER"]="IMM"
BR_WIDTH = 3


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


OPMAP = permutation(OP_SEED)          # raw -> internal op
INV_OPMAP = [0] * 256
for raw, internal in enumerate(OPMAP):
    INV_OPMAP[internal] = raw
SBOX = permutation(SBOX_SEED)
ISBOX = [0] * 256
for i, v in enumerate(SBOX):
    ISBOX[v] = i


def venc(v):
    out = bytearray()
    while True:
        b = (v & 0x7F) << 1
        v >>= 7
        if v:
            out.append(b | 1)
        else:
            out.append(b); break
    return bytes(out)


def read_varint(buf, pc):
    val = 0; shift = 0
    while True:
        b = buf[pc]; pc += 1
        val |= (b >> 1) << shift
        shift += 7
        if not (b & 1):
            break
    return val, pc


def ror8(x, n):
    x &= 0xFF; n &= 7
    return x if n == 0 else ((x >> n) | (x << (8 - n))) & 0xFF


def disasm(buf, start):
    """Linear sweep from `start`; stop when a byte maps to a non-opcode."""
    pc = start
    out = []
    while pc < len(buf):
        raw = buf[pc]
        op = OPMAP[raw]
        if op >= len(NAMES):
            break
        mnem = NAMES[op]
        f = FMT[mnem]
        ipc = pc
        pc += 1
        ins = {"pc": ipc, "op": mnem}
        try:
            if f == "NONE":
                pass
            elif f in ("R1",):
                b = buf[pc]; pc += 1; ins["d"] = b >> 4
            elif f in ("R2",):
                b = buf[pc]; pc += 1; ins["d"] = b >> 4; ins["s"] = b & 0xF
            elif f == "RI":
                b = buf[pc]; pc += 1; ins["d"] = b >> 4
                ins["imm"], pc = read_varint(buf, pc)
            elif f == "RM":
                b = buf[pc]; pc += 1; ins["d"] = b >> 4; ins["base"] = b & 0xF
                ins["off"], pc = read_varint(buf, pc)
            elif f == "BR":
                ins["tgt"], pc = read_varint(buf, pc)
            elif f == "IMM":
                ins["imm"], pc = read_varint(buf, pc)
        except IndexError:
            break
        out.append(ins)
    return out


def find_prog(elf):
    # First instruction: MOVI r14, 0x100  ->  [raw_movi, 0xE0] + venc(0x100)
    sig = bytes([INV_OPMAP[OP["MOVI"]], (14 << 4)]) + venc(0x100)
    idx = elf.find(sig)
    if idx < 0:
        raise SystemExit("could not locate PROG in binary")
    return idx


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: solve.py <path-to-synthvm>")
    path = sys.argv[1]
    elf = open(path, "rb").read()

    start = find_prog(elf)
    ins = disasm(elf, start)

    # L = number of IN opcodes in the read loop
    L = sum(1 for i in ins if i["op"] == "IN")

    # round boundaries: each round begins with MOVI to r6 (the carry seed)
    round_starts = [k for k, i in enumerate(ins)
                    if i["op"] == "MOVI" and i.get("d") == 6]
    R = len(round_starts)

    # compare loop begins at the first CMPI on r1 after the last round
    cmp_start = None
    for k in range(round_starts[-1], len(ins)):
        if ins[k]["op"] == "CMPI" and ins[k].get("d") == 1:
            cmp_start = k
            break
    if cmp_start is None:
        raise SystemExit("could not find compare loop")

    bounds = round_starts + [cmp_start]
    ivs, rots, cs = [], [], []
    for r in range(R):
        blk = ins[bounds[r]:bounds[r + 1]]
        ivs.append(blk[0]["imm"])                       # MOVI r6, IV
        rot = next(i["imm"] for i in blk if i["op"] == "ROL8")
        rots.append(rot)
        cs.append([i["imm"] for i in blk if i["op"] == "XORI" and i.get("d") == 1])
        assert len(cs[-1]) == L, (r, len(cs[-1]), L)

    # target T[] from the compare loop's CMPI immediates
    T = [i["imm"] for i in ins[cmp_start:] if i["op"] == "CMPI" and i.get("d") == 1][:L]
    assert len(T) == L

    # invert the R rounds (last to first)
    a = bytearray(T)
    for r in reversed(range(R)):
        rot = rots[r]
        iv = ivs[r]
        c = cs[r]
        O = bytearray(a)
        for i in range(L):
            t = O[i] ^ c[i]
            t = ror8(t, rot)
            t = ISBOX[t]
            carry = iv if i == 0 else O[i - 1]
            a[i] = (t - carry) & 0xFF
    flag = bytes(a)

    print("[*] PROG @ file offset 0x%x" % start)
    print("[*] L=%d rounds=%d" % (L, R))
    print("[*] recovered flag:", flag.decode(errors="replace"))

    # verify against the real binary
    try:
        r = subprocess.run([path], input=flag, capture_output=True, timeout=30)
        ok = b"Access granted" in r.stdout
        print("[*] binary says:", r.stdout.decode(errors="replace").strip(),
              "=>", "OK" if ok else "FAIL")
        sys.exit(0 if ok else 1)
    except Exception as e:
        print("[!] could not run binary to verify:", e)


if __name__ == "__main__":
    main()
