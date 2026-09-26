# binary-ascii

**Catégorie** warmup · **Points** 50 · **Auteur** dagbanjaphet

# binary-ascii -- solution

## TL;DR

Groups of 8 bits -> ASCII bytes.

## Steps

For each space-separated 8-bit group, `int(group, 2)` gives a byte;
`chr` turns it into a character. Join them all.

Run `python3 solve.py`.

## Flag

`NCTF{…}`
