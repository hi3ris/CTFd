# adv-flip

You are given one file:

- `gate.npz` with three arrays:
  - `w` -- shape `(d,)`, the gate's weight vector.
  - `b` -- shape `(1,)`, the gate's bias.
  - `x0` -- shape `(d,)`, a base input that is currently LOCKED.

The gate scores `s(x) = w . x + b` and unlocks when `s(x) >= 0`. Find the
minimal-norm adversarial input that just unlocks it; that input is the flag
`NCTF{...}`.
