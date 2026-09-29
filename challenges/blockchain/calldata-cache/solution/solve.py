#!/usr/bin/env python3
"""Offline solver: loads shipped artifacts and prints the flag."""

import os


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    raw = open(os.path.join(here, "..", "calldata.txt")).read().strip()
    data = bytes.fromhex(raw[2:] if raw.startswith("0x") else raw)
    args = data[4:]  # drop 4-byte selector
    # ABI: store(uint256 id, address who, string note)
    # word2 is the offset (from start of args) to the string tail
    off = int.from_bytes(args[64:96], "big")
    strlen = int.from_bytes(args[off : off + 32], "big")
    note = args[off + 32 : off + 32 + strlen]
    print(note.decode())


if __name__ == "__main__":
    main()
