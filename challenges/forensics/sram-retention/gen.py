#!/usr/bin/env python3
"""
Author tool: builds the AE-32 SRAM retention dumps for the `sram-retention`
forensics challenge.

This is NOT the solver. It is the ground-truth generator so the challenge is
reproducible. It produces:

    retention.dump           -> the challenge artifact (contains the flag)
    samples/sample_0N.dump   -> worked samples with KNOWN plaintext
    samples/KNOWN.txt        -> the expected decoded string for each sample

Format is the invented "AE-32 SRAM retention image" described in
AE32_SRAM_datasheet.md. See that file for field semantics. Key non-obvious
rules baked in here:

  * Bank base table entries are EOF-RELATIVE: phys = filesize - stored_u16le.
  * The header checksum covers the 7 header bytes ONLY (not the base table).
  * The vault (key) is written round-robin across LOGICAL banks:
        key[k] -> logical bank (k % NBANKS), slot j = (k // NBANKS)
        intra-bank byte offset = VAULT_BASE(4) + j * STRIDE
  * Each bank begins with a 4-byte tag: b"BNK" + bytes([logical_id]).
  * Logical->physical bank order is a permutation (banks are non-contiguous
    and out of order in the file).
"""

import os
import random
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
MAGIC = b"AE32"
VAULT_BASE = 4          # bytes: vault registers start after the 4-byte bank tag
BANK_STRIDE_LEN = 64    # physical span reserved per bank region

FLAG = "NCTF{sram_retention_bank_interleave}"


def retention_noise(rng, n):
    """SRAM decays toward a biased ground state; emulate biased retention noise."""
    out = bytearray(n)
    for i in range(n):
        r = rng.random()
        if r < 0.40:
            out[i] = 0x00
        elif r < 0.80:
            out[i] = 0xFF
        else:
            out[i] = rng.randint(0, 255)
    return out


def build(payload, nbanks, stride, phys_offsets, filesize, seed, decoy=None):
    """
    payload      : bytes to store in the vault (the "key")
    nbanks       : number of logical banks
    stride       : intra-bank spacing between successive vault slots
    phys_offsets : list[nbanks] physical byte offset of LOGICAL bank i
    filesize     : total image size in bytes
    seed         : PRNG seed for retention noise
    decoy        : optional (offset, bytes) contiguous red herring
    """
    assert len(phys_offsets) == nbanks
    rng = random.Random(seed)
    buf = retention_noise(rng, filesize)

    L = len(payload)

    # --- header (8 bytes) ---
    buf[0:4] = MAGIC
    buf[4] = nbanks
    buf[5] = L
    buf[6] = stride
    buf[7] = sum(buf[0:7]) & 0xFF          # checksum over header bytes 0..6 only

    # --- bank base table at 0x08: nbanks * u16 LE, EOF-relative ---
    tbl = 0x08
    for i in range(nbanks):
        stored = filesize - phys_offsets[i]
        assert 0 < stored <= 0xFFFF, stored
        struct.pack_into("<H", buf, tbl + 2 * i, stored)

    # --- bank tags ---
    for i in range(nbanks):
        base = phys_offsets[i]
        buf[base:base + 4] = b"BNK" + bytes([i])

    # --- decoy (contiguous plausible-but-wrong string in the noise) ---
    if decoy is not None:
        off, data = decoy
        buf[off:off + len(data)] = data

    # --- interleaved vault ---
    for k in range(L):
        logical = k % nbanks
        j = k // nbanks
        intra = VAULT_BASE + j * stride
        phys = phys_offsets[logical] + intra
        buf[phys] = payload[k]

    return bytes(buf)


def write(path, data):
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path} ({len(data)} bytes)")


def main():
    os.makedirs(os.path.join(HERE, "samples"), exist_ok=True)

    # ---- the real challenge image ----
    # 5 banks, scattered & permuted, filesize 0x400.
    real = build(
        payload=FLAG.encode(),
        nbanks=5,
        stride=3,
        phys_offsets=[0x300, 0x100, 0x280, 0x1A0, 0x080],
        filesize=0x400,
        seed=0xAE32,
        decoy=(0x040, b"NCTF{cold_boot_dram_dump_not_the_key}"),
    )
    write(os.path.join(HERE, "retention.dump"), real)

    # ---- worked samples with KNOWN plaintext ----
    samples = [
        # (name, payload, nbanks, stride, phys_offsets, filesize, seed)
        ("sample_01", b"HELLO_AE32_WORLD",       3, 2, [0x080, 0x180, 0x100], 0x300, 1),
        ("sample_02", b"retention-check-abc",     4, 3, [0x200, 0x080, 0x180, 0x100], 0x400, 2),
        ("sample_03", b"bank0/bank1/bank2",       3, 4, [0x100, 0x300, 0x200], 0x400, 3),
        ("sample_04", b"AE-32 register file",     5, 2, [0x300, 0x080, 0x280, 0x180, 0x100], 0x400, 4),
        ("sample_05", b"deinterleave_me_now_ok",  6, 3, [0x300, 0x080, 0x340, 0x180, 0x100, 0x280], 0x400, 5),
        ("sample_06", b"vault=noncontiguous",     4, 5, [0x080, 0x300, 0x180, 0x280], 0x400, 6),
    ]
    known = []
    for name, payload, n, stride, offs, fsize, seed in samples:
        data = build(payload, n, stride, offs, fsize, seed)
        write(os.path.join(HERE, "samples", name + ".dump"), data)
        known.append(f"{name}.dump\t{payload.decode()}")

    with open(os.path.join(HERE, "samples", "KNOWN.txt"), "w") as f:
        f.write("# Expected decoded vault contents for each sample dump.\n")
        f.write("# Use these to validate your parser before running on retention.dump.\n")
        f.write("# filename\tdecoded_vault\n")
        f.write("\n".join(known) + "\n")
    print("wrote samples/KNOWN.txt")


if __name__ == "__main__":
    main()
