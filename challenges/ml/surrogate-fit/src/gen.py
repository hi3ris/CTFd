"""Generator for the surrogate-fit challenge (model extraction).

A hidden linear oracle computes ``y = X @ w`` for a secret weight vector ``w``.
We ship a query/response dataset ``(X, y)`` collected within a fixed query
budget. Fitting a least-squares surrogate to ``(X, y)`` recovers ``w`` exactly
because the design matrix is well-conditioned and the responses are noise-free.

The recovered weight vector's rounded bytes ARE the flag.
"""

import numpy as np

FLAG = "NCTF{least_squares_clones_the_oracle}"


def main():
    rng = np.random.default_rng(770011)

    w = np.array([ord(c) for c in FLAG], dtype=np.float64)
    d = w.shape[0]

    # Query budget: a few more queries than dimensions -> overdetermined but
    # comfortably solvable. Small integer probes keep the artifact compact.
    n = d + 8
    X = rng.integers(low=-4, high=5, size=(n, d)).astype(np.float64)

    # Ensure full column rank (avoid a degenerate design matrix).
    while np.linalg.matrix_rank(X) < d:
        X = rng.integers(low=-4, high=5, size=(n, d)).astype(np.float64)

    y = X @ w  # noise-free oracle responses

    np.savez("query_log.npz", X=X.astype(np.float64), y=y.astype(np.float64))
    print("wrote query_log.npz", X.shape, "rank", np.linalg.matrix_rank(X))


if __name__ == "__main__":
    main()
