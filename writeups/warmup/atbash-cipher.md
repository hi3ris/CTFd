# atbash-cipher

**Catégorie** warmup · **Points** 50 · **Auteur** dagbanjaphet

# atbash-cipher -- solution

## TL;DR

Atbash: `A<->Z`, `B<->Y`, .... It is its own inverse.

## Steps

```
tr 'A-Za-z' 'Z-Az-a' < secret.txt   # -> NCTF{…}
```

Or run `python3 solve.py`.

## Flag

`NCTF{…}`
