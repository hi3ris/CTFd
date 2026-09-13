# CoinVault ledger export — file format (`ledger.coinvault`)

A CoinVault table runs a commit-reveal coin-flip game. Each round the dealer
first **seals** its draw (publishes a commitment), then later **opens** it
(reveals the draw so anyone can recheck the seal). This file is a plain-text
export of one table's session. This document tells you only how to *parse* it.

## Encoding

UTF-8 text, one record per line, `\n`-terminated. Lines beginning with `#` are
comments. The first line is the magic `COINVAULT-LEDGER v1`.

### Header

```
P=<hex>          # the field modulus p (a prime). Draws are elements of F_p.
ROUNDS=<int>     # number of opened rounds in this export
```

Let `FE = ceil(bitlength(p) / 8)` be the fixed byte length used to encode a
field element (big-endian, left zero-padded).

### Opened rounds

One line per opened round, index `r = 0 .. ROUNDS-1`:

```
R<rrr>|C=<hex>|Y=<hex>|B=<bit>
```

* `C` — the round's **commitment**, 16 bytes (32 hex chars). It is defined as

  ```
  C = SHA256( Y_bytes || r_bytes )[:16]
  ```

  where `Y_bytes = Y.to_bytes(FE, "big")` and `r_bytes = r.to_bytes(4, "big")`.
  You can (and should) recompute it from `Y` to confirm your parsing.

* `Y` — the round's **draw**, a field element in `F_p`, hex.

* `B` — the published **coin** of the round, equal to `Y mod 2`.

### The vault round

Exactly one line:

```
VAULT|IDX=<int>|C=<hex>|CT=<hex>
```

* `IDX` — the vault round's index (it directly follows the opened rounds).
* `C` — its commitment, formed exactly like `C` above (with `r = IDX`). The
  vault round is **committed but never opened**: its draw `Y` is not in the file.
* `CT` — the sealed vault payload, a byte string (hex). It is the flag XORed
  with a SHA-256 counter-mode keystream keyed by the vault draw `Y_vault`:

  ```
  key    = SHA256( Y_vault.to_bytes(FE, "big") )
  stream = SHA256(key || 0x00000000) || SHA256(key || 0x00000001) || ...
  flag   = CT XOR stream[:len(CT)]
  ```

  So recovering the vault draw `Y_vault` is exactly what unseals the flag.

## What this document does not cover

How the dealer chooses each round's draw `Y`. That is the dealer's internal
business; all you are given is the sealed/opened transcript above. The flag is
`NCTF{...}`.
