# hex-decode -- solution

## TL;DR

`secret.txt` is hex-encoded ASCII. Decode two chars per byte.

## Steps

```
xxd -r -p secret.txt      # -> NCTF{hex_is_just_base_sixteen}
```

Or run `python3 solve.py`.

## Flag

`NCTF{hex_is_just_base_sixteen}`
