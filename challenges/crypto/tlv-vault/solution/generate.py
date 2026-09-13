#!/usr/bin/env python3
"""
VLT1 container generator (challenge authoring tool).

This produces the 8 public sample vaults. The format is INVENTED - it is not
DER, protobuf, or any standard TLV. The deliberately confusing semantics:

  1. Length prefixes count ENTRIES (records), not bytes.
  2. The header checksum covers ONLY the 7 header bytes, not the file.
  3. The ciphertext offset is measured relative to EOF, not start of file.
  4. The 1-byte `version` field is a mask that is XORed into every key byte.

Layout
------
Header (8 bytes, fixed):
    [0:4]  magic  = b"VLT1"
    [4]    version (uint8)          <- key mask
    [5:7]  rec_count (uint16 LE)    <- number of top-level records (NOT bytes)
    [7]    hdr_cksum (uint8)        = sum(bytes[0:7]) & 0xFF  (header only)

Records region (starts at byte 8): rec_count records, concatenated.
Each record:
    [0]    type (uint8)
    [1]    count (uint8)            <- number of ENTRIES (NOT bytes)
    [2:]   entries...               <- count * entry_size(type) bytes

Record types:
    0x4B 'K'  KEY   : each entry = (pos:uint8, kbyte:uint8)   -> 2 bytes/entry
    0x4D 'M'  META  : each entry = value:uint16 LE            -> 2 bytes/entry
                      entry[0] = ct_len   (ciphertext length in bytes)
                      entry[1] = ct_off   (offset of ciphertext from EOF)
    0x53 'S'  SALT  : each entry = 1 random byte  (RESERVED / decoy - ignore)

Trailer:
    ...ciphertext (ct_len bytes)... then a 4-byte footer b"\\x00END".
    So ciphertext_start = filesize - ct_off, where ct_off = ct_len + 4.

Key derivation:
    klen = max(pos over KEY entries) + 1
    key = [0]*klen
    for (pos, kbyte) in KEY entries:  key[pos] = kbyte ^ version
    plaintext[i] = ciphertext[i] ^ key[i % klen]

The flag is STATIC (pure downloadable crypto challenge).
"""
import os
import struct
import random

FOOTER = b"\x00END"

T_KEY = 0x4B
T_META = 0x4D
T_SALT = 0x53

FLAG = b"NCTF{r3c0rds_n0t_byt3s_x0r_v4ult}"

# 7 decoy plaintexts + 1 flag. The flag lives in exactly one sample.
DECOYS = [
    b"vault services log rotation completed at 03:14 utc no anomalies detected",
    b"reminder: rotate the quarterly signing keys before the audit window opens",
    b"telemetry ping ok; container healthy; queue depth nominal; retrying batch",
    b"this record archive is public sample data and contains no secret material",
    b"maintenance note: replace the reserved salt tables during the next deploy",
    b"congratulations you parsed the framing but this blob is only filler text!",
    b"the answer is not here keep looking through the other vaults in the set :)",
]


def build_key(plaintext, version, rng):
    """Pick a key of random length, return (key_bytes, key_entries_shuffled)."""
    klen = rng.choice([5, 6, 7, 8, 9])
    key = bytes(rng.randrange(1, 256) for _ in range(klen))
    entries = list(range(klen))
    rng.shuffle(entries)  # positions stored out of order on purpose
    key_entry_bytes = b"".join(
        struct.pack("BB", pos, key[pos] ^ version) for pos in entries
    )
    return key, klen, key_entry_bytes


def encrypt(plaintext, key):
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(plaintext))


def build_vault(plaintext, seed, with_salt):
    rng = random.Random(seed)
    version = rng.randrange(1, 256)

    key, klen, key_entry_bytes = build_key(plaintext, version, rng)
    ct = encrypt(plaintext, key)
    ct_len = len(ct)
    ct_off = ct_len + len(FOOTER)  # offset measured from EOF

    # KEY record
    key_rec = struct.pack("BB", T_KEY, klen) + key_entry_bytes
    # META record: 2 entries (ct_len, ct_off), each uint16 LE
    meta_rec = struct.pack("BB", T_META, 2) + struct.pack("<HH", ct_len, ct_off)

    records = []
    # Randomise record order to force real parsing, not positional guessing.
    core = [key_rec, meta_rec]
    if with_salt:
        n_salt = rng.choice([3, 4, 5])
        salt_rec = struct.pack("BB", T_SALT, n_salt) + bytes(
            rng.randrange(0, 256) for _ in range(n_salt)
        )
        core.append(salt_rec)
    rng.shuffle(core)
    records = core

    rec_count = len(records)
    # Header: cksum over the 7 header bytes only.
    head7 = b"VLT1" + struct.pack("B", version) + struct.pack("<H", rec_count)
    cksum = sum(head7) & 0xFF
    header = head7 + struct.pack("B", cksum)

    body = header + b"".join(records) + ct + FOOTER
    return body


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "public")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # Fixed order of plaintexts; flag placed at a non-obvious index (sample 5).
    flag_index = 4  # 0-based -> vault_05
    plaintexts = list(DECOYS)
    plaintexts.insert(flag_index, FLAG)  # now 8 entries

    for i, pt in enumerate(plaintexts, start=1):
        with_salt = (i % 2 == 0)  # half the samples carry the decoy SALT record
        blob = build_vault(pt, seed=1000 + i, with_salt=with_salt)
        path = os.path.join(out_dir, f"vault_{i:02d}.vlt")
        with open(path, "wb") as f:
            f.write(blob)
        print(f"wrote {path} ({len(blob)} bytes, salt={with_salt})")

    print("flag is in vault_%02d" % (flag_index + 1))


if __name__ == "__main__":
    main()
