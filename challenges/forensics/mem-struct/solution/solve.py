#!/usr/bin/env python3
"""Reference solver for mem-struct.

    python3 solve.py ../memdump.bin

Find the ``secret_record`` by its magic, read the offset/length/key, then XOR the
flag bytes back with the repeating 4-byte little-endian key.
"""
import struct
import sys

MAGIC = 0x0FF5E7ED


def main(path: str) -> None:
    data = open(path, "rb").read()
    needle = struct.pack("<I", MAGIC)
    rec_off = data.find(needle)
    if rec_off < 0:
        raise SystemExit("magic not found")

    magic, xor_key, flag_off, flag_len = struct.unpack(
        "<IIII", data[rec_off : rec_off + 16]
    )
    assert magic == MAGIC
    key_bytes = struct.pack("<I", xor_key)
    obf = data[flag_off : flag_off + flag_len]
    flag = bytes(b ^ key_bytes[i % 4] for i, b in enumerate(obf)).decode()
    print(flag)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../memdump.bin")
