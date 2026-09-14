# mask-slip — solution

## TL;DR

GitHub Actions masks only the _literal_ secret string in logs. The workflow
pipes the secret through `base64` "for debugging", and that transformed output
is not masked. Base64-decode the leaked line in `run.log` to get the secret,
which is the flag.

## The misconfiguration

Secret masking is a substring replacement: the runner scans each log line for
the exact registered secret and swaps it for `***`. It has no idea that
`base64`, `rev`, `xxd`, or a byte-splitting `echo` produce reversible encodings
of the same secret. The `Debug token (base64)` step therefore prints the secret
verbatim in encoded form:

```yaml
- name: Debug token (base64)
  run: |
    echo -n "$DEPLOY_TOKEN" | base64
```

The direct-echo step correctly shows `using token: ***`; the base64 step leaks.

## Attack

1. In `run.log`, find the output of the step whose group header mentions
   `base64`.
2. Base64-decode that line.
3. The decoded bytes are the secret — here the flag itself.

## Run

```
python3 solve.py
```

Output:

```
[+] leaked base64 in log: TkNURntjaV9zZWNyZXRf...
[+] FLAG = NCTF{ci_secret_masking_is_only_literal_b64}
```

## Files

- `../.github/workflows/deploy.yml` — the CI pipeline.
- `../run.log` — the captured job log.
- `../src/gen.py` — deterministic builder.
- `solve.py` — reference solver (stdlib only).
