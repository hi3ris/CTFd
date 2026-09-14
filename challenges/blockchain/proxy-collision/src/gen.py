#!/usr/bin/env python3
"""Regenerate proxy_storage.json for proxy-collision (deterministic)."""

import json

FLAG = "NCTF{delegatecall_hits_slot0}"


def word(v):
    return "0x" + v.to_bytes(32, "big").hex()


def main():
    s = {}
    fb = FLAG.encode()
    s[word(0)] = "0x" + (fb + b"\x00" * (32 - len(fb))).hex()
    s[word(1)] = word(int("0x00000000000000000000000000000000deadbeef", 16))
    s[word(2)] = word(0)
    dec = b"NCTF{wrong_slot_try_the_collision}"[:32]
    s[word(3)] = "0x" + (dec + b"\x00" * (32 - len(dec))).hex()
    with open("proxy_storage.json", "w") as f:
        json.dump(s, f, indent=2, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main()
