# surrogate-fit

You are given one file:

- `query_log.npz` with two arrays:
  - `X` -- shape `(n, d)`, the inputs sent to the hidden model.
  - `y` -- shape `(n,)`, the model's exact scalar output for each input.

Reconstruct the hidden model's parameters. Interpreted correctly, they are the
flag `NCTF{...}`.
