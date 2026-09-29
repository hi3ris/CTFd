# base32-decode -- solution

## TL;DR

`secret.txt` is Base32 (`A-Z2-7` + `=`). Decode it.

## Steps

```
base32 -d secret.txt      # -> NCTF{base32_uses_more_letters}
```

Or run `python3 solve.py`.

## Flag

`NCTF{base32_uses_more_letters}`
