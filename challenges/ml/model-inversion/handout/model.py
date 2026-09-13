#!/usr/bin/env python3
"""
model.py -- the AEGIS-VAULT "sealed record recall" scorer (handout / white-box).

This is the EXACT code the live oracle runs, with one thing removed: the
memorised record `r`. `E` is shipped in weights.npz. The record `r` is the
per-team secret the live vault memorised -- it is never in these files and never
returned by the API.

You can instantiate `Vault` with a record you choose and call `confidence(...)`
to reproduce the oracle offline for your own testing.
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
