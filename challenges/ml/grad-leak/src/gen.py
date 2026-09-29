"""Generator for the grad-leak challenge.

A single linear layer ``y = W @ x`` is trained on ONE private example. We ship
the gradient of the loss w.r.t. the weight matrix (``dL/dW``) together with the
upstream gradient ``dL/dy``. Because a linear layer's weight gradient is the
rank-one outer product ``dL/dW = (dL/dy) @ x.T``, any row of the shipped matrix
divided by the matching ``dL/dy`` entry reconstructs the private input ``x``.

The private input's bytes ARE the flag. Nothing else is shipped.
"""

import numpy as np

FLAG = "NCTF{rank_one_grad_rebuilds_the_input}"


def main():
    rng = np.random.default_rng(20240517)

    # Private training input: its bytes are the flag.
    x = np.array([ord(c) for c in FLAG], dtype=np.float64)
    d_in = x.shape[0]
    d_out = 6

    # Upstream gradient dL/dy for the single example (deterministic, nonzero).
    # Integers keep the shipped artifact exact; the sign varies per unit.
    g = rng.integers(low=-9, high=9, size=d_out).astype(np.float64)
    g[g == 0] = 3.0  # guarantee every row is usable

    # Weight gradient of a linear layer is the rank-one outer product.
    grad_W = np.outer(g, x)

    np.savez(
        "leaked_grads.npz",
        grad_W=grad_W.astype(np.float64),
        dL_dy=g.astype(np.float64),
    )
    print("wrote leaked_grads.npz", grad_W.shape)


if __name__ == "__main__":
    main()
