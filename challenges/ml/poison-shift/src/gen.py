"""Generator for the poison-shift challenge (data poisoning).

We ship a regression training set ``(X, y)`` labelled by a clean linear rule
plus a handful of POISONED samples that do not lie on the clean hyperplane.
The poisoned points are exactly the ones that tug the fitted boundary; they
reveal themselves as large-residual outliers under a robust fit.

Sorting the poisoned samples by id and reading their character tags spells the
flag.
"""

import numpy as np

FLAG = "NCTF{outlier_influence_tips_the_boundary}"


def main():
    rng = np.random.default_rng(135791)

    flag_chars = list(FLAG)
    n_poison = len(flag_chars)
    n_clean = 460
    d = 5

    # Clean linear rule (small integer weights + bias).
    w_true = rng.integers(-3, 4, size=d).astype(np.float64)
    b_true = 2.0

    total = n_clean + n_poison
    all_ids = rng.permutation(total)
    poison_ids = np.sort(all_ids[:n_poison])  # ascending -> flag order

    X = rng.uniform(-3, 3, size=(total, d))
    y = X @ w_true + b_true  # start everything on the clean plane
    tags = np.zeros(total, dtype=np.int64)

    poison_set = set(int(p) for p in poison_ids)
    # Map id -> row index is identity here (id == row index).
    for pos, pid in enumerate(poison_ids):
        # Corrupt the label far off the clean plane (large residual).
        y[pid] += rng.choice([-1.0, 1.0]) * rng.uniform(15.0, 28.0)
        tags[pid] = ord(flag_chars[pos])

    # Clean rows get a neutral tag (space) so only poison tags matter.
    for i in range(total):
        if i not in poison_set:
            tags[i] = ord(" ")

    ids = np.arange(total, dtype=np.int64)
    np.savez(
        "poisoned_train.npz",
        record_id=ids,
        X=X.astype(np.float64),
        y=y.astype(np.float64),
        tag=tags,
    )
    print("wrote poisoned_train.npz  rows", total, " poison", n_poison)


if __name__ == "__main__":
    main()
