# zip-carve — writeup

**Category:** forensics · **Difficulty:** easy
**Flag:** `NCTF{orphan3d_l0cal_h34d3r_c4rv3d}` (static)

## One-line summary

A ZIP member exists in the byte stream but was deleted from the central
directory; carve the orphaned `PK\x03\x04` local file header to recover it.

## Technique

A ZIP file has two copies of its file metadata: a **local file header** in front
of each member's data, and a **central directory** at the end of the archive
that every tool actually reads. `archive.zip` has been edited so the central
directory lists only the decoy `notes.txt`, while the local header and stored
bytes of `secret.txt` remain untouched in the stream. `unzip -l`, `zipinfo`, and
Python's `zipfile` therefore never reveal `secret.txt`.

## Step by step

1. `zipinfo archive.zip` (or Python `zipfile.namelist()`) shows only
   `notes.txt`, yet the file is bigger than that member.
2. Search the raw bytes for every local file header signature `PK\x03\x04`.
   There are two.
3. Parse the second header (name length, compressed size, method = stored) and
   read out its data — this is `secret.txt`.
4. It contains `internal recovery token -> NCTF{...}`.

Tools like `binwalk archive.zip` or `foremost` also surface the second member.

## Run the reference solver

```
python3 solve.py ../archive.zip
```

## Flag

`NCTF{orphan3d_l0cal_h34d3r_c4rv3d}`
