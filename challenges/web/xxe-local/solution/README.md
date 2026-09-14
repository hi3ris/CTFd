# xxe-local -- solution

**Summary:** The XML parser has external general entities enabled and a
resolver that reads local files, so the captured invoice's `SYSTEM "secret.flag"`
entity discloses the flag.

## Vulnerability

`app.py` builds a SAX parser with `feature_external_ges = True` and a
`LocalResolver` that opens SYSTEM ids straight off disk -- textbook XXE local
file disclosure. `invoice.xml` declares:

```
<!ENTITY xxe SYSTEM "secret.flag">
```

and expands `&xxe;` inside `<note>`, so parsing it reads `secret.flag` (shipped
in the working directory) into the response.

## Steps

1. Note the DOCTYPE entity and the enabled external-entity feature.
2. Parse `invoice.xml` with the same resolver, resolving `secret.flag` against
   the shipped files.
3. The expanded `<note>` text is the flag.

Run:

```
python3 solution/solve.py
```

## Flag

```
NCTF{external_entity_reads_the_local_secret_file}
```
