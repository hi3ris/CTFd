"""Find the poisoned samples as large-residual outliers and read the flag."""

import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "..", "poisoned_train.npz")


def main():
    data = np.load(ART)
    ids = data["record_id"]
    X = data["X"]
    y = data["y"]
    tag = data["tag"]

    # Fit a linear model to all data, then flag the samples whose residual is
    # far larger than the bulk (the clean samples lie on the hyperplane).
    A = np.hstack([X, np.ones((X.shape[0], 1))])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = np.abs(y - A @ coef)

    # Robust cutoff: many-sigma above the median absolute residual.
    med = np.median(resid)
    mad = np.median(np.abs(resid - med)) + 1e-9
    poison = resid > med + 6.0 * mad

    poison_ids = ids[poison]
    poison_tags = tag[poison]
    order = np.argsort(poison_ids)
    flag = "".join(chr(int(t)) for t in poison_tags[order])
    print(flag)


if __name__ == "__main__":
    main()
