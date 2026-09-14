# sqlite-union -- solution

**Summary:** The search endpoint concatenates `q` into a SQL string, so a
`UNION SELECT` reads the secret out of a second table in the shipped `shop.db`.

## Vulnerability

`app.py` builds:

```
SELECT id, name, price FROM products WHERE name LIKE '%<q>%'
```

with `<q>` taken verbatim from the request. Classic union-based SQL injection.
The database ships as `shop.db`, so the same query runs offline.

## Steps

1. Enumerate tables in `shop.db` (there is a `flags` table alongside
   `products`).
2. Match the three-column shape of the outer query with a payload:
   `' UNION SELECT id, secret, 0 FROM flags -- `.
3. Execute the resulting SQL against `shop.db`; the flag comes back in the
   `name` position.

Run:

```
python3 solution/solve.py
```

## Flag

```
NCTF{union_select_the_hidden_admin_secret_row}
```
