#!/usr/bin/env python3
"""
model.py -- the AEGIS-VAULT "sealed record recall" scorer (server copy).

A tiny, fully self-contained similarity classifier in pure NumPy. During
provisioning the vault "memorises" one D-dimensional record `r` (the sealed
record). The public API is a two-class confidence oracle:

    OTHER    the probe does not resemble the sealed record   (reference logit 0)
    SEALED   the probe resembles the sealed record

The SEALED logit is a learned bilinear similarity between the probe and the
memorised record under a fixed, team-common metric M:

    s(p) = (p/255)^T  M  (r/255)  +  C0            # M = E^T E  (symmetric PD)
    P(SEALED | p) = softmax([s(p), 0])[0] = sigmoid(s(p))

The embedding matrix `E` (hence the metric `M = E^T E`) is FIXED for every team
and shipped white-box in `weights.npz`. Only the memorised record `r` is
per-team, and it is NEVER shipped or returned -- it is derived at instance start
from the per-challenge secret and lives only in the running instance's memory.

The SAME scoring code (minus the record derivation) is shipped to the player as
the handout `model.py`, so the function the player reasons about locally is the
function the server evaluates.
"""
import hashlib
import hmac
import math
import os

import numpy as np

# ---- fixed, team-common architecture constants -----------------------------
D = 24            # length of the sealed record (attribute bytes, 0..255)
DEMB = 40         # embedding dimension (> D, so M = E^T E is positive definite)
S = 255.0         # attribute scale (bytes are normalised by S)
C0 = -1.5         # fixed bias on the SEALED logit (team-common)

CLASSES = ["OTHER", "SEALED"]
SEALED = 1
OTHER = 0

# The seed pins the team-common embedding so `build_model.py` is deterministic:
# the image rebuilds byte-identical weights, and every team shares the metric.
BUILD_SEED = 0xC0FFEE24

_HERE = os.path.dirname(os.path.abspath(__file__))


def build_embedding(seed: int = BUILD_SEED) -> np.ndarray:
    """Deterministically construct the team-common embedding E (DEMB x D).

    Gaussian columns give a well-conditioned, full-column-rank E, so the metric
    M = E^T E is symmetric positive definite (and therefore invertible)."""
    rng = np.random.default_rng(seed)
    return (rng.standard_normal((DEMB, D)) / math.sqrt(DEMB)).astype(np.float64)


class Vault:
    """Loads the fixed embedding and scores probes against a memorised record."""

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


# ---- per-team record derivation (SERVER ONLY -- not in the handout) ---------
def derive_record(secret: str) -> np.ndarray:
    """Deterministically expand the per-challenge secret into the D-byte record.

    Distinct from the flag derivation (which uses CHALLENGE_SECRET[:24]); the
    record and the flag are independent projections of the same secret, so the
    record cannot be read off the flag or vice versa."""
    out = bytearray()
    i = 0
    while len(out) < D:
        out.extend(hmac.new(secret.encode(),
                            b"model-inversion-record|%d" % i,
                            hashlib.sha256).digest())
        i += 1
    return np.frombuffer(bytes(out[:D]), dtype=np.uint8).astype(np.int64)
