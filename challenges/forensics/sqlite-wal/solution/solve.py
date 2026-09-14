#!/usr/bin/env python3
"""Reference solver for sqlite-wal.

    python3 solve.py ../app.db

Opening app.db together with its -wal replays the redacting UPDATE, so the live
value is ``REDACTED``. The pre-redaction value was never checkpointed into the
main file, so we open the *main file alone* (copied away from its -wal) and read
the original flag.
"""
import os
import shutil
import sqlite3
import sys
import tempfile


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

    print(rows[0][0])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../app.db")
