"""Generator for the trojan-trigger challenge (backdoor trigger recovery).

A shipped detector unit scores an input by how closely it matches a hidden
memory pattern: ``score(x) = c - ||E @ x - m||^2``. The unit is dormant for
ordinary inputs and fires (score -> maximum) only for the trigger that drives
``E @ x`` onto the memory ``m``. Recovering the trigger is a least-squares
problem: ``x* = pinv(E) @ m``.

The memory is built as ``m = E @ f`` where ``f`` holds the flag bytes, and
``E`` has full column rank, so the recovered trigger is exactly ``f``.
"""

import numpy as np

FLAG = "NCTF{pinv_wakes_the_dormant_neuron}"


def main():
    rng = np.random.default_rng(9090909)

    f = np.array([ord(c) for c in FLAG], dtype=np.float64)
    d = f.shape[0]
    h = d + 5  # more detector rows than input dims -> full column rank

    E = rng.standard_normal((h, d))
    while np.linalg.matrix_rank(E) < d:
        E = rng.standard_normal((h, d))

    m = E @ f  # hidden memory pattern the trigger must reproduce
    c = float(rng.integers(1000, 2000))  # cosmetic score offset

    np.savez(
        "detector.npz",
        E=E.astype(np.float64),
        m=m.astype(np.float64),
        c=np.array([c], dtype=np.float64),
    )
    print("wrote detector.npz", E.shape, "rank", np.linalg.matrix_rank(E))


if __name__ == "__main__":
    main()
