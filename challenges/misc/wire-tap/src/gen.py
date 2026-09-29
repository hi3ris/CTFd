#!/usr/bin/env python3
"""Emit message.bin: a hand-built protobuf wire-format message for wire-tap.

Schema (implicit -- players must recover it from the wire bytes):

    field 1, varint            : format version
    field 2, varint            : single-byte XOR key
    field 3, varint (repeated) : decoy timestamps
    field 4, length-delimited  : nested message
        field 1, varint            : fragment count
        field 2, length-delimited  : flag bytes XORed with the key

The flag never appears in plaintext, so ``strings`` on the blob reveals
nothing.
"""

import os

FLAG = b"NCTF{protobuf_is_just_tagged_varints}"
KEY = 0x5A


def varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def tag(field: int, wire: int) -> bytes:
    return varint((field << 3) | wire)


def ld(field: int, data: bytes) -> bytes:
    return tag(field, 2) + varint(len(data)) + data


def vint(field: int, value: int) -> bytes:
    return tag(field, 0) + varint(value)


def main() -> None:
    xored = bytes(b ^ KEY for b in FLAG)
    nested = vint(1, len(FLAG)) + ld(2, xored)

    msg = vint(1, 3)  # version
    msg += vint(2, KEY)  # xor key
    for ts in (1726300000, 1726300123, 1726300999):
        msg += vint(3, ts)  # decoy repeated field
    msg += ld(4, nested)

    out = os.path.join(os.path.dirname(__file__), "..", "message.bin")
    with open(out, "wb") as fh:
        fh.write(msg)
    print("wrote", os.path.relpath(out), "bytes:", len(msg))


if __name__ == "__main__":
    main()
