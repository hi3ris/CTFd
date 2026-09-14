# sqlite-wal — writeup

**Category:** forensics · **Difficulty:** hard
**Flag:** `NCTF{wr1t3_4h34d_l0g_l34ks_0ld_r0w}` (static)

## One-line summary

The redaction lives only in the write-ahead log; the main `app.db` file was
never checkpointed, so opening it without its `-wal` reveals the original token.

## Technique

SQLite WAL divergence. The database was built like this:

1. Insert `recovery_token = NCTF{...}` and **checkpoint**, so the flag is written
   into the main `app.db` file and the WAL is emptied.
2. `UPDATE ... SET value = 'REDACTED...'` and commit, but **do not checkpoint**.
   That change is recorded only in a fresh `app.db-wal`.

So the two files disagree:

- `app.db` + `app.db-wal` together (the normal way SQLite opens it) -> SQLite
  replays the WAL and you read `REDACTED-by-dlp-policy`.
- `app.db` **alone** -> the un-checkpointed main file still contains the original
  `recovery_token` page.

## Step by step

1. `sqlite3 app.db "SELECT * FROM secrets"` shows the redacted token (the WAL is
   replayed).
2. Copy `app.db` into an empty directory, leaving `app.db-wal` behind.
3. Open that lone copy: `sqlite3 main.db "SELECT * FROM secrets"`. Now nothing
   replays the redaction and the original `recovery_token` is the flag.

You can also carve it without SQLite at all: the string is present verbatim in
the main `app.db` file (`strings app.db | grep NCTF`), while the WAL holds the
`REDACTED` page — inspecting both shows the before/after.

## Run the reference solver

```
python3 solve.py ../app.db
```

The solver copies only the main file (deliberately not its `-wal`) into a temp
directory and reads the row, so it never mutates the shipped artifact.

## Flag

`NCTF{wr1t3_4h34d_l0g_l34ks_0ld_r0w}`
