#!/usr/bin/env python3
"""
Solver for tlv-vault.

Parses every VLT1 sample with the CORRECT (invented) semantics and prints the
decrypted plaintext of each. The one that starts with NCTF{ is the flag.

Key inference points (the traps):
  * record `count` bytes and the header `rec_count` count ENTRIES, not bytes,
    so a byte-length parser walks off the rails immediately.
  * ciphertext is located as filesize - ct_off  (offset from EOF).
  * each stored key byte is XORed with the header `version` to get the real
    key byte (raw XOR without the mask yields near-garbage -> the tell).
  * record type 0x53 (SALT) is reserved noise and must be ignored.
"""
import glob
import os
import struct
import sys

T_KEY = 0x4B
T_META = 0x4D
T_SALT = 0x53

ENTRY_SIZE = {T_KEY: 2, T_META: 2, T_SALT: 1}


def parse(blob):
    assert blob[0:4] == b"VLT1", "bad magic"
    version = blob[4]
    rec_count = struct.unpack_from("<H", blob, 5)[0]
    hdr_cksum = blob[7]
    assert (sum(blob[0:7]) & 0xFF) == hdr_cksum, "header checksum mismatch"

    off = 8
    key = None
    ct_len = ct_off = None
    for _ in range(rec_count):          # loop by RECORD COUNT, not bytes
        rtype = blob[off]
        count = blob[off + 1]           # count = number of ENTRIES
        esz = ENTRY_SIZE[rtype]
        payload = blob[off + 2: off + 2 + count * esz]
        off += 2 + count * esz

        if rtype == T_KEY:
            klen = count
            kbytes = [0] * klen
            for i in range(count):
                pos, kb = payload[2 * i], payload[2 * i + 1]
                kbytes[pos] = kb ^ version      # unmask with version
            key = bytes(kbytes)
        elif rtype == T_META:
            ct_len = struct.unpack_from("<H", payload, 0)[0]
            ct_off = struct.unpack_from("<H", payload, 2)[0]
        elif rtype == T_SALT:
            pass                                # reserved decoy: ignore
        else:
            raise ValueError("unknown record type 0x%02x" % rtype)

    filesize = len(blob)
    start = filesize - ct_off                   # offset relative to EOF
    ct = blob[start:start + ct_len]
    pt = bytes(b ^ key[i % len(key)] for i, b in enumerate(ct))
    return pt


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    pub = os.path.join(here, "..", "public")
    flag = None
    for path in sorted(glob.glob(os.path.join(pub, "*.vlt"))):
        try:
            pt = parse(open(path, "rb").read())
        except Exception as e:
            print(f"{os.path.basename(path)}: parse error: {e}")
            continue
        try:
            text = pt.decode("ascii")
        except UnicodeDecodeError:
            text = repr(pt)
        print(f"{os.path.basename(path)}: {text}")
        if text.startswith("NCTF{"):
            flag = text
    print("\nFLAG:", flag)
    return 0 if flag else 1


if __name__ == "__main__":
    sys.exit(main())
