#!/usr/bin/env python3
"""Parse the framed byte stream, drop bad-CRC frames, reassemble DATA by seq."""

import os

SOF = 0xAA
OP_DATA = 0x10
OP_END = 0x30


def crc(body):
    x = 0
    for b in body:
        x ^= b
    return x


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    hexstr = "".join(open(os.path.join(here, "..", "stream.hex")).read().split())
    data = bytes.fromhex(hexstr)

    i = 0
    chunks = {}
    while i < len(data):
        assert data[i] == SOF, "lost frame sync at %d" % i
        op = data[i + 1]
        seq = data[i + 2]
        ln = (data[i + 3] << 8) | data[i + 4]
        payload = data[i + 5 : i + 5 + ln]
        got = data[i + 5 + ln]
        body = data[i + 1 : i + 5 + ln]
        frame_len = 1 + 4 + ln + 1
        if op == OP_END:
            break
        if crc(body) == got and op == OP_DATA:
            chunks[seq] = payload
        i += frame_len

    flag = b"".join(chunks[s] for s in sorted(chunks))
    print(flag.decode())


if __name__ == "__main__":
    main()
