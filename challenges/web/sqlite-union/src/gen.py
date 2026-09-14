#!/usr/bin/env python3
"""Producer for sqlite-union artifact (shop.db)."""

import os
import sqlite3

FLAG = "NCTF{union_select_the_hidden_admin_secret_row}"


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
    db.execute("CREATE TABLE flags(id INTEGER PRIMARY KEY, label TEXT, secret TEXT)")
    db.execute("INSERT INTO flags(label, secret) VALUES(?, ?)", ("ops-portal", FLAG))
    db.commit()
    db.close()


if __name__ == "__main__":
    main()
