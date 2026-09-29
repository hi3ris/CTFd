# base64-decode -- solution

## TL;DR

`secret.txt` is Base64. Decode it.

## Steps

1. Notice the alphabet: `A-Z a-z 0-9 + /` with `=` padding -- that is Base64.
2. Decode it:

```
base64 -d secret.txt      # -> NCTF{base64_is_not_encryption}
```

Or run `python3 solve.py`.

## Flag

`NCTF{base64_is_not_encryption}`
