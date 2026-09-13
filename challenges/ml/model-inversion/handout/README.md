# AEGIS-VAULT — sealed record recall (handout)

The vault has **memorised one record**: `D = 24` attribute bytes, each `0..255`.
The public API is a **confidence oracle** — it will only tell you, for a probe
you supply, how strongly it *recalls* that probe as the sealed record. It never
shows you the record. Your job: recover the sealed record and hand it back.

## Files

| file | what |
|---|---|
| `weights.npz` | the embedding `E` (key `E`, shape `40 x 24`). White-box, same for every team. |
| `model.py` | the **exact** scoring code the oracle runs, minus the record. `Vault.score(probe, record)`, `Vault.confidence(probe, record)`. The similarity metric is `M = E.T @ E`. |
| `README.md` | this file |

The memorised record is **not** in any file here and is never returned by the
API — it is per-team and lives only in the running instance. The flag is emitted
only by `/submit`, only when the record you return matches. Flag: `NCTF{...}`.

## The scorer (white-box)

```python
s(p) = (p/255)^T  M  (r/255)  +  C0          # M = E^T E,  C0 = -1.5
P(SEALED | p) = softmax([0, s(p)])[1] = sigmoid(s(p))
```

`M` is symmetric positive definite (E has full column rank), and it is **not**
diagonal — the confidence for a probe mixes all attributes of the record
together, so it is a *similarity*, not a per-attribute readout. Probing one
attribute at a time does not hand back that attribute's value.

You can reproduce the oracle exactly for any record of your own and test your
recovery offline before hitting the live instance:

```python
from model import Vault, D
import numpy as np
v = Vault("weights.npz")
r = np.random.randint(0, 256, D)             # a record only you know
print(v.confidence([0]*D, r))                # what the live API would answer
# ... recover r using confidence() as a black box, then compare ...
```

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
doubles, so nothing here is noisy — the recovery is a clean, closed-form
inversion once you see what the oracle is actually leaking.
