"""Fit a least-squares surrogate to the query log and read off the flag."""

import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "..", "query_log.npz")


def main():
    data = np.load(ART)
    X = data["X"]
    y = data["y"]

    # Ordinary least squares recovers the oracle's weight vector exactly.
    w, *_ = np.linalg.lstsq(X, y, rcond=None)

    recovered = np.rint(w).astype(int)
    flag = "".join(chr(v) for v in recovered)
    print(flag)


if __name__ == "__main__":
    main()
