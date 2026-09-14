#!/usr/bin/env python3
"""Find the rendezvous datetime in the SMS, look up the GPS fix at that exact
timestamp, and use its coordinates to decrypt the self-note."""

import hashlib
import os
import re
import sqlite3
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BACKUP = os.path.join(ROOT, "backup")


def keystream(key: str, n: int) -> bytes:
    out = bytearray()
    c = 0
    while len(out) < n:
        out += hashlib.sha256(key.encode() + c.to_bytes(4, "big")).digest()
        c += 1
    return bytes(out[:n])


def main() -> None:
    msg = sqlite3.connect(os.path.join(BACKUP, "messages.sqlite"))
    bodies = [r[0] for r in msg.execute("SELECT body FROM sms")]
    iso = next(
        re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", b).group(0)
        for b in bodies
        if "RDV confirme" in b
    )
    rdv_ts = int(
        datetime.strptime(iso, "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=timezone.utc)
        .timestamp()
    )

    loc = sqlite3.connect(os.path.join(BACKUP, "location.sqlite"))
    lat, lon = loc.execute(
        "SELECT lat, lon FROM locations WHERE ts = ?", (rdv_ts,)
    ).fetchone()

    key = f"{lat:.6f},{lon:.6f}"
    (cipher,) = msg.execute("SELECT cipher FROM notes").fetchone()
    plain = bytes(a ^ b for a, b in zip(cipher, keystream(key, len(cipher)))).decode()
    flag = re.search(r"token=(NCTF\{[^}]+\})", plain).group(1)
    print(flag)


if __name__ == "__main__":
    main()
