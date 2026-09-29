#!/usr/bin/env python3
"""Correlate the two exports by shared email, then XOR-decrypt the hex backup
key with the matching Mastodon handle."""

import json
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def main() -> None:
    with open(os.path.join(ROOT, "telegram_export.json")) as fh:
        tg = json.load(fh)
    with open(os.path.join(ROOT, "mastodon_export.json")) as fh:
        masto = json.load(fh)

    pivot_email = tg["account"]["email_on_file"]

    # find the Mastodon account that reuses the same email
    key = next(a["username"] for a in masto["accounts"] if a["email"] == pivot_email)

    # extract the hex ciphertext from the backup-key message
    hexblob = next(
        re.search(r"hex=([0-9a-f]+)", m["text"]).group(1)
        for m in tg["messages"]
        if "hex=" in m["text"]
    )

    ct = bytes.fromhex(hexblob)
    kb = key.encode()
    flag = bytes(b ^ kb[i % len(kb)] for i, b in enumerate(ct)).decode()
    print(flag)


if __name__ == "__main__":
    main()
