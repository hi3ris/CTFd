# base64-decode

**Catégorie** warmup · **Points** 50 · **Auteur** dagbanjaphet

# base64-decode -- solution

## TL;DR

`secret.txt` is Base64. Decode it.

## Steps

1. Notice the alphabet: `A-Z a-z 0-9 + /` with `=` padding -- that is Base64.
2. Decode it:

```
base64 -d secret.txt      # -> NCTF{…}
```

Or run `python3 solve.py`.

## Flag

`NCTF{…}`
