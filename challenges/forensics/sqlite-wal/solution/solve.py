#!/usr/bin/env python3
"""Reference solver for sqlite-wal.

    python3 solve.py ../app.db

Opening app.db together with its -wal replays the redacting UPDATE, so the live
value is ``REDACTED``. The pre-redaction value was never checkpointed into the
main file, so we open the *main file alone* (copied away from its -wal) and read
the original row.

That row is not the flag in cleartext: it is ``base64(single-byte-XOR(flag))``.
We base64-decode it and brute-force the single XOR byte (no shared key needed) —
the correct key is the one that yields the ``NCTF{`` prefix.
"""
import base64
import os
import shutil
import sqlite3
import sys
import tempfile


def decode_token(encoded: str) -> str:
    blob = base64.b64decode(encoded)
    for key in range(256):
        cand = bytes(b ^ key for b in blob)
        if cand.startswith(b"NCTF{") and cand.endswith(b"}"):
            return cand.decode("latin-1")
    raise ValueError("could not recover flag from stored token")


def main(path: str) -> None:
    tmp = tempfile.mkdtemp(prefix="wal_solve_")
    # Copy ONLY the main db file — deliberately leaving the -wal behind, so
    # SQLite reads the un-checkpointed main file as-is.
    lone = os.path.join(tmp, "main.db")
    shutil.copy(path, lone)

    con = sqlite3.connect(lone)
    con.execute("PRAGMA journal_mode=DELETE")  # ensure no WAL is consulted
    rows = con.execute(
        "SELECT value FROM secrets WHERE name='recovery_token'"
    ).fetchall()
    con.close()
    shutil.rmtree(tmp, ignore_errors=True)

    print(decode_token(rows[0][0]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../app.db")
