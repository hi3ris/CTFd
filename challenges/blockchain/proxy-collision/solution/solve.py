#!/usr/bin/env python3
"""Offline solver: loads shipped artifacts and prints the flag."""

import json
import os


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    dump = json.load(open(os.path.join(here, "..", "proxy_storage.json")))
    # Logic.value is at slot 0; under delegatecall it aliases Proxy slot 0
    # (Proxy.implementation). The clobbered slot 0 holds the note.
    slot0 = "0x" + (0).to_bytes(32, "big").hex()
    word = bytes.fromhex(dump[slot0][2:])
    print(word.rstrip(b"\x00").decode())


if __name__ == "__main__":
    main()
