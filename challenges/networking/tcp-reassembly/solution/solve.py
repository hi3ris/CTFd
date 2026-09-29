#!/usr/bin/env python3
"""Reassemble the TCP byte stream from out-of-order, absolute-seq segments."""

import json
import os

MOD = 1 << 32


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    doc = json.load(open(os.path.join(here, "..", "segments.json")))
    segs = doc["segments"]

    # ISN comes from the SYN segment; data starts at ISN+1.
    isn = None
    for s in segs:
        if "SYN" in s["flags"]:
            isn = s["seq"]
    assert isn is not None, "no SYN"
    origin = (isn + 1) % MOD

    buf = {}
    for s in segs:
        data = bytes.fromhex(s["data"])
        if not data:
            continue
        offset = (s["seq"] - origin) % MOD
        for k, byte in enumerate(data):
            pos = offset + k
            if pos in buf:
                assert buf[pos] == byte, "conflicting overlap at %d" % pos
            else:
                buf[pos] = byte

    length = max(buf) + 1
    assert all(p in buf for p in range(length)), "gap in stream"
    out = bytes(buf[p] for p in range(length))
    print(out.decode())


if __name__ == "__main__":
    main()
