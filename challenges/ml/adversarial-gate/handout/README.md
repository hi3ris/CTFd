# SENTRY-6 badge gate — handout

The gate scores a **32x32 single-channel** badge (uint8, 0..255) with a small
CNN and opens only for class **GRANTED**. Your job: from the shipped `DENIED`
badge, craft a badge classified `GRANTED` while staying within **L-inf
epsilon = 8** raw levels, wrap it in a **QGP1** packet, and `POST` it to the
live instance's `/submit`.

## Files

| file | what |
|---|---|
| `weights.npz` | model weights: `Wc1,bc1,Wc2,bc2,Wf,bf` |
| `gatemodel.py` | the **exact** model: `GateModel.logits`, `.predict`, and `logits_and_input_grad(img, target)` returning `d(logit_target)/d(pixel)`. Pure NumPy — the same code the server runs, so a white-box attack transfers with no framework mismatch. No autograd needed. |
| `denied_badge.npy` | the `DENIED` badge as a decoded 32x32 uint8 array |
| `denied_badge.gatepkt` | the same badge in the QGP1 container |
| `samples/badge_*.gatepkt` | six more badges in QGP1 |
| `samples/badge_00.npy`, `badge_01.npy` | two of them decoded, so you can check your codec against ground truth |

The model:

```python
from gatemodel import GateModel, CLASSES, GRANTED
import numpy as np
m = GateModel("weights.npz")
denied = np.load("denied_badge.npy")
print(CLASSES[m.predict(denied)])          # -> DENIED
logits, grad = m.logits_and_input_grad(denied, GRANTED)   # grad wrt uint8 pixels
```

Preprocessing (already inside the model, but you need it if you reimplement):
`x = (pixel/255 - 0.5) / 0.5`, single channel, shape `(1,32,32)`.

## QGP1 container — partial spec

`/submit` accepts **only** the QGP1 container. It is not PNG, NPY, DER or
protobuf. Header is 12 bytes, little-endian where multi-byte:

```
[0:4]   magic     b"QGP\x01"
[4]     nrows     uint8
[5]     ncols     uint8
[6]     flags     uint8   (bit0 has meaning — compare a decoded sample to its .npy)
[7]     reserved  uint8   (0)
[8:10]  hdr_sum   uint16  a checksum — but over WHAT bytes exactly? (look closely)
[10:12] rec_count uint16  a count — of bytes, or of something else?
```

Body: a sequence of records, each `[len:1][len bytes]`.

Three of the conventions here are **not** what you'd assume from a normal image
container. The `samples/*.npy` pairs are ground truth: decode a sample your way,
diff against its `.npy`, and fix your reader until they match exactly. A
malformed packet is rejected by the gate with a specific error message, which
is a useful signal while you dial in the encoder.

## Submit

```
POST /submit   Content-Type: application/json
{"badge": "<base64 of your QGP1 packet>"}
# or raw:
POST /submit   Content-Type: application/octet-stream
<QGP1 packet bytes>
```

The server decodes your packet, verifies `max|badge - DENIED| <= 8` on the
integer pixel plane, runs the real classifier, and returns the flag only if the
result is `GRANTED`. Unlimited attempts. Flag format: `CTF{...}`.

Hint: target GRANTED **specifically**. An untargeted step usually lands on the
nearest wrong class, not GRANTED — and the epsilon check is on integers, so
round/clip into `{denied±8} ∩ [0,255]` before you submit.
