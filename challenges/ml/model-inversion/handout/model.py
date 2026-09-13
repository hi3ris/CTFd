#!/usr/bin/env python3
"""
model.py -- the AEGIS-VAULT "sealed record recall" scorer (handout / white-box).

This is the EXACT code the live oracle runs, with one thing removed: the
memorised record `r`. Everything about how a probe is scored is here, so you can
reproduce the oracle for any record of your own choosing and check your work
offline before touching the live instance.

The similarity metric is a fixed, team-common bilinear form:

    s(p) = (p/255)^T  M  (r/255)  +  C0            # M = E^T E  (symmetric PD)
    P(SEALED | p) = softmax([0, s(p)])[1] = sigmoid(s(p))

`E` is shipped in weights.npz; `M = E^T E`. The record `r` is the per-team
secret the live vault memorised -- it is never in these files and never returned
by the API. Your task is to recover it from the confidence oracle alone.

Quick self-test (pick any record you like and confirm you can recover it from
confidences only):

    from model import Vault, D
    import numpy as np
    v = Vault("weights.npz")
    r = np.random.randint(0, 256, D)          # a record only YOU know
    conf = v.confidence(np.zeros(D, int), r)  # what the live API would return
    #   ... now try to recover r using confidence() as a black box ...
"""
import math
import os

import numpy as np

# ---- fixed, team-common architecture constants -----------------------------
D = 24            # length of the sealed record (attribute bytes, 0..255)
DEMB = 40         # embedding dimension
S = 255.0         # attribute scale
C0 = -1.5         # fixed bias on the SEALED logit (team-common)

CLASSES = ["OTHER", "SEALED"]
SEALED = 1
OTHER = 0

_HERE = os.path.dirname(os.path.abspath(__file__))


class Vault:
    """Loads the fixed embedding and scores probes against a record."""

    def __init__(self, weights_path: str | None = None):
        if weights_path is None:
            weights_path = os.path.join(_HERE, "weights.npz")
        with np.load(weights_path) as z:
            self.E = z["E"].astype(np.float64)
        self.M = self.E.T @ self.E            # (D, D) symmetric positive definite

    def score(self, probe, record) -> float:
        """SEALED logit s(p) = (p/S)^T M (r/S) + C0."""
        p = np.asarray(probe, dtype=np.float64).reshape(D)
        r = np.asarray(record, dtype=np.float64).reshape(D)
        return float((p / S) @ self.M @ (r / S)) + C0

    def confidence(self, probe, record) -> dict:
        """Two-class softmax {OTHER: logit 0, SEALED: s(p)} -> probabilities."""
        s = self.score(probe, record)
        z = np.array([0.0, s], dtype=np.float64)     # [OTHER, SEALED]
        z = z - z.max()
        e = np.exp(z)
        prob = e / e.sum()
        return {"OTHER": float(prob[0]), "SEALED": float(prob[1])}
