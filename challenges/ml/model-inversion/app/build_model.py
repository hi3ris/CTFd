#!/usr/bin/env python3
"""
build_model.py -- construct the team-common AEGIS-VAULT metric at image build.

Deterministic (fixed seed): writes `weights.npz` containing the single array
`E` (the DEMB x D embedding). The similarity metric the oracle uses is
M = E^T E; it is not stored separately because any holder of E can form it.

Run at image build:   python build_model.py
Run locally the same way to reproduce byte-identical weights.

No secret is involved here -- the embedding is common to all teams. The per-team
record is derived at instance start from the per-challenge secret (see model.py
`derive_record`) and never touches disk.
"""
import os

import numpy as np

from model import build_embedding, D, DEMB

_HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    E = build_embedding()
    assert E.shape == (DEMB, D)
    M = E.T @ E
    # sanity: M must be invertible for the recovery to be well-posed
    eig = np.linalg.eigvalsh(M)
    assert eig.min() > 1e-6, "metric M is near-singular; pick another seed"
    out = os.path.join(_HERE, "weights.npz")
    np.savez(out, E=E.astype(np.float64))
    print(f"[build] wrote {out}  E={E.shape}  cond(M)={np.linalg.cond(M):.1f}")


if __name__ == "__main__":
    main()
