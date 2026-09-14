# rot13-decode -- solution

## TL;DR

ROT13. Applying ROT13 again reverses it.

## Steps

```
tr 'A-Za-z' 'N-ZA-Mn-za-m' < secret.txt   # -> NCTF{rot13_twice_is_nothing}
```

Or run `python3 solve.py`.

## Flag

`NCTF{rot13_twice_is_nothing}`
