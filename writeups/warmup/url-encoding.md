# url-encoding

**Catégorie** warmup · **Points** 50 · **Auteur** dagbanjaphet

# url-encoding -- solution

## TL;DR

Percent-encoding (URL encoding). `%7B` = `{`, `%5F` = `_`, etc.

## Steps

```
python3 -c "import urllib.parse;print(urllib.parse.unquote(open('../encoded.txt').read().strip()))"
```

-> `NCTF{…}`

Or run `python3 solve.py`.

## Flag

`NCTF{…}`
