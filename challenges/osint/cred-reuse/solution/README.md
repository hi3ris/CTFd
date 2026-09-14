# cred-reuse — writeup

**Category:** osint · **Difficulty:** medium
**Flag:** `NCTF{cr3d_reuse_forum_to_admin_portal}`

## Summary

Crack a leaked forum hash dump with the supplied wordlist, find the account that
reused its password on the admin-portal, and use that password to decrypt the
admin note.

## Technique

Offline hash cracking (SHA-1 vs wordlist) + credential-reuse pivot across a
service registry + a sha256-CTR keystream decrypt.

## Step by step

1. Hash every word in `wordlist.txt` with SHA-1 and match against `dump.txt`.
   Most accounts crack.
2. Read `services.csv`. Find the cracked email registered on both `forum` and
   `admin-portal`: `afi.doe@webmail.tg`, password `Lome228!`. (`root.admin@cert.tg`
   is on the admin-portal but not in the forum breach, so it cannot be cracked —
   a dead end.)
3. `admin_portal.enc` is XOR-encrypted with a keystream derived from the reused
   password: `keystream = sha256(pass || counter_be32)` concatenated over
   `counter = 0,1,2,...`.
4. Decrypt and read the `jeton de secours` line — the flag.

Run `python3 solution/solve.py` to reproduce.

## Flag

`NCTF{cr3d_reuse_forum_to_admin_portal}`
