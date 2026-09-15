#!/usr/bin/env python3
"""Generate ``app.db`` (+ ``app.db-wal``) for the sqlite-wal challenge.

A SQLite database in WAL (write-ahead log) mode. The flag is first written and
checkpointed into the *main* database file. Then the row is UPDATED to
``REDACTED`` and committed, but **not** checkpointed, so that change lives only
in the ``-wal`` sidecar. Consequences:

* Opening the pair normally (sqlite3 replays the WAL) shows ``REDACTED``.
* Opening the main ``app.db`` file *without* its ``-wal`` shows the original
  (obfuscated) token that was never overwritten in the main file.

The token itself is **not** stored in cleartext. The recovery_token row holds
``base64(single-byte-XOR(flag))``, so ``strings app.db | grep NCTF`` finds
nothing — the player must recover the pre-redaction row *and* undo the encoding.

The artifact ships both ``app.db`` and ``app.db-wal``.
"""
import base64
import os
import shutil
import sqlite3
import tempfile

FLAG = "NCTF{wr1t3_4h34d_l0g_l34ks_0ld_r0w}"
REDACTED = "REDACTED-by-dlp-policy"

# Obfuscation applied to the stored recovery_token so a raw `strings` sweep of
# the main db page cannot reveal the flag. Single-byte XOR keeps it brute-force
# recoverable without a shared key (scan 0..255 for the NCTF{ prefix).
XOR_KEY = 0x5A


def encode_token(flag: str) -> str:
    xored = bytes(b ^ XOR_KEY for b in flag.encode())
    return base64.b64encode(xored).decode("ascii")


def main() -> None:
    workdir = tempfile.mkdtemp(prefix="sqlitewal_")
    dbp = os.path.join(workdir, "app.db")

    con = sqlite3.connect(dbp)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA wal_autocheckpoint=0")  # never auto-checkpoint
    con.execute("CREATE TABLE secrets (id INTEGER PRIMARY KEY, name TEXT, value TEXT)")
    con.executemany(
        "INSERT INTO secrets (id, name, value) VALUES (?, ?, ?)",
        [
            (1, "smtp_password", "hunter2"),
            (2, "api_key", "sk-live-0000-1111-2222"),
            (3, "recovery_token", encode_token(FLAG)),
            (4, "note", "rotate all creds quarterly"),
        ],
    )
    con.commit()

    # Force the flag into the MAIN db file and empty the WAL.
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    # Now redact the token; this commit lands ONLY in the fresh WAL.
    con.execute("UPDATE secrets SET value=? WHERE name='recovery_token'", (REDACTED,))
    con.commit()

    # Snapshot both files while the connection is still open, so no
    # close-time checkpoint can fold the WAL back into the main file.
    shutil.copy(dbp, "app.db")
    shutil.copy(dbp + "-wal", "app.db-wal")

    con.close()
    shutil.rmtree(workdir, ignore_errors=True)

    print(
        f"wrote app.db ({os.path.getsize('app.db')} bytes) + "
        f"app.db-wal ({os.path.getsize('app.db-wal')} bytes); flag={FLAG}"
    )


if __name__ == "__main__":
    main()
