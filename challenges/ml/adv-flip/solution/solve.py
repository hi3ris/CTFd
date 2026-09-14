"""Craft the minimum-norm adversarial step that unlocks the linear gate."""

import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "..", "gate.npz")


def main():
    data = np.load(ART)
    w = data["w"]
    b = float(data["b"][0])
    x0 = data["x0"]

    s0 = float(w @ x0 + b)
    # Closed-form minimum-norm perturbation to reach s(x) = 0.
    delta = -(s0 / float(w @ w)) * w
    adv = x0 + delta

    recovered = np.rint(adv).astype(int)
    flag = "".join(chr(v) for v in recovered)
    print(flag)


if __name__ == "__main__":
    main()
