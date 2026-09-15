#!/usr/bin/env python3
"""Producer for sqlite-union artifact (shop.db).

The flag is NOT stored in the clear. It lives in a hidden `secrets` table as a
hex-encoded ciphertext (`cipher`) that is XORed with a repeating key held in a
*different* column of the same row (`xkey`). Neither column alone reveals the
flag, so `strings shop.db | grep NCTF` finds nothing: the player must UNION
SELECT to reach the row, combine the two columns, and decode.
"""

import os
import sqlite3

FLAG = "NCTF{union_select_the_hidden_admin_secret_row}"
# Repeating-key XOR key, stored in its own column so the UNION must pull both.
XKEY = "kente-souvenirs"


def seal(plaintext: str, key: str) -> str:
    kb = key.encode()
    pb = plaintext.encode()
    return bytes(b ^ kb[i % len(kb)] for i, b in enumerate(pb)).hex()


def main() -> None:
    if os.path.exists("shop.db"):
        os.remove("shop.db")
    db = sqlite3.connect("shop.db")
    db.execute(
        "CREATE TABLE products(id INTEGER PRIMARY KEY, name TEXT, price INTEGER)"
    )
    db.executemany(
        "INSERT INTO products(name, price) VALUES(?, ?)",
        [
            ("Kente Mug", 1200),
            ("Ntoma Tote", 3500),
            ("Akwaaba Cap", 1800),
            ("Sankofa Pin", 800),
        ],
    )
    # cipher = hex(flag XOR repeat(xkey)); decode = bytes.fromhex(cipher) XOR xkey.
    db.execute(
        "CREATE TABLE secrets(id INTEGER PRIMARY KEY, label TEXT, cipher TEXT, xkey TEXT)"
    )
    db.execute(
        "INSERT INTO secrets(label, cipher, xkey) VALUES(?, ?, ?)",
        ("flag: xor(fromhex(cipher), repeat(xkey))", seal(FLAG, XKEY), XKEY),
    )
    db.commit()
    db.close()


if __name__ == "__main__":
    main()
