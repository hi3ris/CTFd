#!/usr/bin/env python3
"""Reference solver for intel-hex.

Parse the Intel HEX file into a flat memory image, read the flag bytes at the
documented offset (0x40), and swap each byte's nibbles to recover ASCII.
"""

import os
import sys

FLAG_OFFSET = 0x0040
FLAG_LEN = 34  # len("NCTF{intel_hex_offset_nibble_swap}")


def parse_ihex(path):
    mem = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith(":"):
                continue
            raw = bytes.fromhex(line[1:])
            count = raw[0]
            addr = (raw[1] << 8) | raw[2]
            rectype = raw[3]
            data = raw[4 : 4 + count]
            checksum = raw[4 + count]
            assert (sum(raw[: 4 + count]) + checksum) & 0xFF == 0, "bad checksum"
            if rectype == 0x00:
                for i, b in enumerate(data):
                    mem[addr + i] = b
            elif rectype == 0x01:
                break
    return mem


def swap_nibbles(b):
    return ((b << 4) & 0xF0) | ((b >> 4) & 0x0F)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, os.pardir, "image.hex")
    mem = parse_ihex(path)
    raw = bytes(mem[FLAG_OFFSET + i] for i in range(FLAG_LEN))
    flag = bytes(swap_nibbles(b) for b in raw).decode("ascii", "replace")
    print(flag)


if __name__ == "__main__":
    main()
