# ecb-echo — solution

## TL;DR

The logged service encrypts `AES-ECB(your_input || SECRET)`. ECB is
deterministic per block, so the secret leaks one byte at a time. The log already
contains the aligned target block and per-guess candidate blocks for each secret
position, so recovery is a block-match lookup.

## Technique

In ECB mode each 16-byte block is encrypted independently, so equal plaintext
blocks give equal ciphertext blocks. Because the secret is appended to attacker
input, you can push the first unknown secret byte to the end of a block by
sending `16 - 1 - (i mod 16)` filler bytes. The ciphertext block then depends on
`filler || known_secret_prefix || <one unknown byte>`. Comparing it against the
same block built from `filler || known_secret_prefix || guess` for each possible
`guess` reveals the byte when they match.

## Attack

1. From `probe` (ciphertext of `"A"*k`), confirm the block size is 16 by finding
   where the ciphertext length jumps.
2. For each entry in `steps`, take `target` (the aligned block for that secret
   position) and scan `candidates` (block hex per printable guess). The guess
   whose block equals `target` is that secret byte.
3. Concatenate the recovered bytes to read the flag.

## Run

```
python3 solve.py            # defaults to ../oracle_log.json
python3 solve.py /path/to/oracle_log.json
```

Output:

```
[+] block size = 16
[+] FLAG = NCTF{ecb_leaks_appended_secrets_one_byte_per_query}
```

## Files

- `../src/gen.py` — deterministic builder for the oracle log (not shipped).
- `../oracle_log.json` — the player handout.
- `solve.py` — this reference solver (Python stdlib only).
