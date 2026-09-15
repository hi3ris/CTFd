# atbash-cipher -- solution

## TL;DR

Atbash: `A<->Z`, `B<->Y`, .... It is its own inverse.

## Steps

```
tr 'A-Za-z' 'Z-Az-a' < secret.txt   # -> NCTF{atbash_mirrors_the_alphabet}
```

Or run `python3 solve.py`.

## Flag

`NCTF{atbash_mirrors_the_alphabet}`
