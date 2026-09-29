# rot47-decode -- solution

## TL;DR

ROT47 over printable ASCII (33-126). Apply it again to reverse.

## Steps

Rotate each byte in `!`..`~` by 47: `chr(33 + (ord(c) - 33 + 47) % 94)`.

Run `python3 solve.py`.

## Flag

`NCTF{rot47_shifts_the_glyphs}`
