"""Reconstruct the private input from the shipped rank-one weight gradient."""

import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "..", "leaked_grads.npz")


def main():
    data = np.load(ART)
    grad_W = data["grad_W"]
    g = data["dL_dy"]

    # dL/dW = g @ x.T  ->  row i is g[i] * x. Use any row with a nonzero scalar.
    i = int(np.argmax(np.abs(g)))
    x = grad_W[i] / g[i]

    recovered = np.rint(x).astype(int)
    flag = "".join(chr(v) for v in recovered)
    print(flag)


if __name__ == "__main__":
    main()
