#!/usr/bin/env python3
"""Reference solver for firmware-blob.

Parse the FWB1 header and section table, read the `.key` and `.flag` sections,
and XOR-decode `.flag` with the repeating key.
"""

import os
import struct
import sys

HDR = struct.Struct("<4sHH")
ENT = struct.Struct("<8sIII")


def parse(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, version, n = HDR.unpack_from(data, 0)
    assert magic == b"FWB1", "bad magic"
    sections = {}
    off = HDR.size
    for _ in range(n):
        name, s_off, length, flags = ENT.unpack_from(data, off)
        off += ENT.size
        name = name.rstrip(b"\x00").decode()
        sections[name] = {
            "data": data[s_off : s_off + length],
            "flags": flags,
        }
    return version, sections


def xor(data, key):
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, os.pardir, "firmware.bin")
    version, sections = parse(path)
    sys.stderr.write(f"version=0x{version:04x} sections={list(sections)}\n")

    key = sections[".key"]["data"]
    flag_sec = sections[".flag"]
    payload = flag_sec["data"]
    if flag_sec["flags"] & 1:  # XOR-encoded
        payload = xor(payload, key)
    print(payload.decode("ascii", "replace"))


if __name__ == "__main__":
    main()
