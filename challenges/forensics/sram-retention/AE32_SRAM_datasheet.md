# Aetheris AE-32 — SRAM Retention Image (partial datasheet)

> Confidential engineering extract. Covers only the fields needed to interpret a
> `.dump` produced by the AE-32 debug probe's "retention capture" command. Timing,
> ECC, and power-domain sections are omitted.

The AE-32 is a fictional microcontroller. Its on-die SRAM is organised as a
**banked register file**. The debug probe snapshots the raw physical SRAM after a
brown-out event; because the banks are physically scattered across the die, they
appear in the dump **out of order and non-contiguous**, separated by regions of
decayed retention noise. A small configuration block at the start of the image
tells you where each bank landed.

All multi-byte integers are **little-endian**.

## 1. Image header (offset 0x00, 8 bytes)

| Offset | Size | Field       | Meaning                                                   |
|-------:|-----:|-------------|-----------------------------------------------------------|
| 0x00   | 4    | `MAGIC`     | ASCII `"AE32"` (0x41 0x45 0x33 0x32).                      |
| 0x04   | 1    | `NBANKS`    | Number of logical banks in the register file.             |
| 0x05   | 1    | `VAULT_LEN` | Length in bytes of the key held in the vault.             |
| 0x06   | 1    | `STRIDE`    | Intra-bank spacing between successive vault slots (bytes). |
| 0x07   | 1    | `HCK`       | Header checksum. See note.                                 |

**Header checksum (`HCK`).** `HCK = (sum of the seven bytes at 0x00..0x06) mod 256`.
It validates the header block **only**. It deliberately does **not** cover the bank
base table or any bank contents — do not expect a whole-image checksum.

## 2. Bank base table (offset 0x08)

Immediately after the header sits the bank base table: `NBANKS` consecutive
**u16 little-endian** entries. Entry `i` gives the physical location of **logical
bank `i`**.

The stored value is **not** an absolute offset. It is measured **from the end of
the image** (end-of-file relative), so:

```
phys_offset(bank i) = image_size - table_entry[i]
```

Because the table is in logical order but the stored offsets are arbitrary, the
logical→physical mapping is a permutation: logical bank 0 is not necessarily the
first bank in the file.

## 3. Bank layout

Each bank begins with a 4-byte **bank tag** so a bank can be identified once
located:

```
byte 0..2 : ASCII "BNK"
byte 3    : logical bank id (0-based)
```

The vault registers begin immediately after the tag, i.e. at intra-bank byte
offset **4**. Everything else in a bank's physical span is unrelated register
state or retention noise.

## 4. Vault (key) storage

The key is not stored contiguously. On write, the controller distributes the key
**round-robin across the logical banks**, one byte at a time:

```
key byte k  ->  logical bank ( k mod NBANKS )
                slot          j = ( k div NBANKS )
                intra-bank offset = 4 + j * STRIDE
```

So consecutive key bytes go to different banks; within one bank the key bytes it
receives are spaced `STRIDE` apart, starting 4 bytes past the tag. To recover the
key, locate every bank via the base table and de-interleave in the same order.

## 5. Retention noise

Regions outside the header, base table, and bank spans hold decayed SRAM. After a
brown-out, uninitialised cells settle toward a biased ground state (heavy `0x00`
and `0xFF`), so plain ASCII you find lying in that noise is **not** part of the
vault — the vault only ever lives inside tagged banks and is assembled by the
interleave rule above.

## 6. Worked samples

`samples/` contains several `.dump` images built with this exact format but
different `NBANKS`/`STRIDE`/permutations, together with `samples/KNOWN.txt` giving
the plaintext each one's vault decodes to. Use them to confirm your parser before
running it on `retention.dump`.
