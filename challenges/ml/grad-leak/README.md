# grad-leak

You are given one file:

- `leaked_grads.npz` with two arrays:
  - `grad_W` -- shape `(d_out, d_in)`, the gradient of the loss w.r.t. a linear
    layer's weight matrix `W` for one training step.
  - `dL_dy` -- shape `(d_out,)`, the upstream gradient for that same step.

The step used a single private input `x` of length `d_in`. Recover `x`; its
bytes are the flag `NCTF{...}`.
