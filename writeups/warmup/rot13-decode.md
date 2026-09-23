# rot13-decode

**Catégorie** warmup · **Points** 50 · **Auteur** dagbanjaphet

# rot13-decode -- solution

## TL;DR

ROT13. Applying ROT13 again reverses it.

## Steps

```
tr 'A-Za-z' 'N-ZA-Mn-za-m' < secret.txt   # -> NCTF{…}
```

Or run `python3 solve.py`.

## Flag

`NCTF{…}`
