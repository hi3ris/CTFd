# trojan-trigger

You are given one file:

- `detector.npz` with three arrays:
  - `E` -- shape `(h, d)`, the detector's projection matrix.
  - `m` -- shape `(h,)`, the detector's hidden memory vector.
  - `c` -- shape `(1,)`, a constant offset.

The detector scores an input as `score(x) = c - ||E @ x - m||^2`. Recover the
trigger `x` that maximizes the score; its bytes are the flag `NCTF{...}`.
