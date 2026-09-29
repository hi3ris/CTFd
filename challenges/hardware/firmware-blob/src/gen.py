#!/usr/bin/env python3
"""Generate a tiny firmware image blob with a simple header + section table.

Layout (all integers little-endian):

  magic       4s   "FWB1"
  version     u16
  n_sections  u16
  --- then n_sections section-table entries, 20 bytes each ---
  name        8s   (NUL-padded)
  offset      u32  (from start of file)
  length      u32
  flags       u32  (bit0 = section is XOR-encoded)
  --- then the raw section payloads at their offsets ---

Sections:
  .boot  plaintext boot banner
  .key   the repeating XOR key
  .flag  the flag, XOR-encoded (flags bit0 set) with the .key bytes
"""

import os
import struct

FLAG = b"NCTF{xor_section_firmware_unpacked}"
KEY = b"\x5a\x13\xa7\x6c"
BANNER = b"bootloader v1.2 (c) acme embedded\x00"

HDR = struct.Struct("<4sHH")
ENT = struct.Struct("<8sIII")


def xor(data, key):
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, os.pardir, "firmware.bin")

    sections = [
        (b".boot", BANNER, 0),
        (b".key", KEY, 0),
        (b".flag", xor(FLAG, KEY), 1),  # flags bit0 = XOR-encoded
    ]

    header_size = HDR.size + ENT.size * len(sections)
    blob = bytearray()
    offset = header_size
    table = []
    for name, payload, flags in sections:
        table.append((name, offset, len(payload), flags))
        blob += payload
        offset += len(payload)

    out_bytes = bytearray()
    out_bytes += HDR.pack(b"FWB1", 0x0102, len(sections))
    for name, off, length, flags in table:
        out_bytes += ENT.pack(name.ljust(8, b"\x00"), off, length, flags)
    out_bytes += blob

    with open(out, "wb") as f:
        f.write(out_bytes)

    print("wrote", os.path.abspath(out), "size:", len(out_bytes))


if __name__ == "__main__":
    main()
