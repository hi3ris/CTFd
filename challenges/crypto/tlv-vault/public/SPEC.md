# VLT1 container format - PARTIAL specification

You have recovered eight `.vlt` files produced by an internal "vault" archiver.
Only a partial spec survived. The rest you must infer from the samples.

Each file begins with the ASCII magic `VLT1`.

## Header (fixed, 8 bytes)

| offset | size | field       | notes                                             |
|-------:|-----:|-------------|---------------------------------------------------|
| 0      | 4    | `magic`     | `VLT1`                                             |
| 4      | 1    | `version`   | format version byte. It is **also mixed into the key material.** |
| 5      | 2    | `rec_count` | uint16, little-endian. Number of **records**.      |
| 7      | 1    | `hdr_cksum` | integrity byte. It covers the **header only**.     |

> Note: `hdr_cksum` is a simple additive checksum of the header bytes that
> precede it. If you try to checksum the whole file you will be disappointed.

## Records region

Immediately after the header come `rec_count` records, back to back.
Records may appear in **any order**.

Every record starts with:

| offset | size | field   | notes                                                   |
|-------:|-----:|---------|---------------------------------------------------------|
| 0      | 1    | `type`  | record type tag                                         |
| 1      | 1    | `count` | number of **entries** in this record (NOT a byte count) |

...followed by `count` entries. The size of one entry depends on `type`.

### Known record types

- `0x4B` **KEY** - carries the XOR key schedule.
  Each entry is 2 bytes: `(position, stored_byte)`.
  Entries are not guaranteed to be in position order, and positions are
  0-based. The real key byte at each position is *not* the stored byte as-is;
  the `version` field is involved. (Recovering ASCII plaintext confirms when
  you have it right.)

- `0x4D` **META** - two uint16 (little-endian) entries:
  `entry[0]` = ciphertext length in bytes,
  `entry[1]` = ciphertext offset. The offset is measured **from the end of the
  file** (EOF), not from the start.

- `0x53` **SALT** - reserved. One byte per entry. Not used by current readers;
  ignore it.

## Payload

The encrypted blob is a repeating-key XOR ciphertext. Locate it using the META
record, decrypt with the KEY schedule, and read the plaintext.

## Flag

Exactly one of the eight vaults decrypts to the flag. Flag format: `CTF{...}`.
