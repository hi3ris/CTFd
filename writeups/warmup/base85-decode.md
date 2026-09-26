# base85-decode

**Catégorie** warmup · **Points** 50 · **Auteur** dagbanjaphet

# base85-decode -- solution

## TL;DR

`secret.txt` is Base85 (`base64.b85` variant). Decode it.

## Steps

```
python3 -c "import base64;print(base64.b85decode(open('../secret.txt').read().strip()).decode())"
```

-> `NCTF{…}`

Or run `python3 solve.py`.

## Flag

`NCTF{…}`
