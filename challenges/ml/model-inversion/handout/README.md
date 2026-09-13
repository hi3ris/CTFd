# AEGIS-VAULT — sealed record recall (handout)

The vault has **memorised one record**: `D = 24` attribute bytes, each `0..255`.
The public API is a **confidence oracle** — for a probe you supply, it tells you
only how strongly it *recalls* that probe as the sealed record. It never shows
you the record. Your job: recover the sealed record and hand it back.

## Files

| file | what |
|---|---|
| `weights.npz` | the embedding `E` (key `E`, shape `40 x 24`). White-box, same for every team. |
| `model.py` | the **exact** scoring code the oracle runs, minus the record. Read it. |
| `README.md` | this file |

The memorised record is **not** in any file here and is never returned by the
API — it is per-team and lives only in the running instance. The flag is emitted
only by `/submit`, and only when the record you return matches. Flag: `NCTF{...}`.

You have the exact scorer (`model.py`) and the weights: everything about how a
probe is scored is in your hands. You can instantiate the scorer with a record
**you** choose and reproduce the oracle offline to develop and test your
approach before touching the live instance.

## API

```
POST /query    Content-Type: application/json
{"probe": [24 ints 0..255]}                  # or {"probes": [[...], ...]} (<=64)
-> {"confidence": {"OTHER": p0, "SEALED": p1}}   # softmax over two classes

POST /submit   Content-Type: application/json
{"record": [24 ints 0..255]}
-> the flag, iff  max|record - r| <= 2   (L-inf, server-side, vs the memorised record)
```

Unlimited queries (a generous rate limit only). The confidences are exact
doubles.
