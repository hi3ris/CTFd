"""Recover the dormant detector's trigger by maximizing its activation."""

import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "..", "detector.npz")


def main():
    data = np.load(ART)
    E = data["E"]
    m = data["m"]

    # score(x) = c - ||E x - m||^2 is maximized where E x = m.
    # Least-squares / pseudo-inverse gives the trigger exactly (E is full rank).
    x_star = np.linalg.pinv(E) @ m

    recovered = np.rint(x_star).astype(int)
    flag = "".join(chr(v) for v in recovered)
    print(flag)


if __name__ == "__main__":
    main()
