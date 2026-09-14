#!/usr/bin/env python3
"""Decode message.bin's protobuf wire format and un-XOR the flag."""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "..", "message.bin")


def read_varint(data: bytes, i: int):
    shift = 0
    result = 0
    while True:
        b = data[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, i
        shift += 7


def parse(data: bytes) -> dict:
    fields = {}
    i = 0
    while i < len(data):
        key, i = read_varint(data, i)
        field, wire = key >> 3, key & 0x7
        if wire == 0:
            value, i = read_varint(data, i)
        elif wire == 2:
            length, i = read_varint(data, i)
            value = data[i : i + length]
            i += length
        else:
            raise ValueError(f"unsupported wire type {wire}")
        fields.setdefault(field, []).append(value)
    return fields


def main() -> None:
    with open(BIN, "rb") as fh:
        top = parse(fh.read())

    key = top[2][0]
    nested = parse(top[4][0])
    xored = nested[2][0]
    flag = bytes(b ^ key for b in xored)
    print(flag.decode())


if __name__ == "__main__":
    main()
