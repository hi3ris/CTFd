"""Generator for the adv-flip challenge (adversarial example).

A linear gate scores an input with ``s(x) = w . x + b``. It is LOCKED while
``s(x) < 0`` and UNLOCKS the instant ``s(x) >= 0``. We ship the gate weights
``(w, b)`` and one base input ``x0`` that is currently LOCKED.

The gate is constructed so that the *minimum-norm* perturbation that just
reaches the decision boundary lands on a very specific point -- and that point's
bytes ARE the flag. The min-norm step for a linear gate is closed form:
``delta* = -(s(x0) / ||w||^2) * w``.
"""

import numpy as np

FLAG = "NCTF{min_norm_step_crosses_the_gate}"


def main():
    rng = np.random.default_rng(31337)

    # Target point on the boundary: its bytes are the flag.
    f = np.array([ord(c) for c in FLAG], dtype=np.float64)
    d = f.shape[0]

    # Random gate normal. Bias placed so the boundary passes exactly through f.
    w = rng.integers(low=-6, high=7, size=d).astype(np.float64)
    w[w == 0] = 2.0
    b = -float(w @ f)  # => s(f) = 0 exactly

    # Base input sits on the LOCKED side, offset from f along -w so that the
    # minimum-norm step back to the boundary is exactly (f - x0).
    alpha = 1.0
    x0 = f - alpha * w
    s0 = float(w @ x0 + b)
    assert s0 < 0, "base input must be locked"

    np.savez(
        "gate.npz",
        w=w.astype(np.float64),
        b=np.array([b], dtype=np.float64),
        x0=x0.astype(np.float64),
    )
    print("wrote gate.npz  dim", d, " s(x0)=", s0)


if __name__ == "__main__":
    main()
