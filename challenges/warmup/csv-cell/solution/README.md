# csv-cell -- solution

## TL;DR

The flag is one cell of `roster.csv`.

## Steps

```
grep -o 'NCTF{[^,]*}' roster.csv   # -> NCTF{hidden_in_one_cell}
```

Or open it in any spreadsheet program and scan the `note` column.
Run `python3 solve.py`.

## Flag

`NCTF{hidden_in_one_cell}`
