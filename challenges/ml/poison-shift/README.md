# poison-shift

You are given one file:

- `poisoned_train.npz` with four arrays (same length, one entry per row):
  - `record_id` -- integer id of the row.
  - `X` -- shape `(n, d)`, features.
  - `y` -- shape `(n,)`, regression target.
  - `tag` -- a single character code attached to the row.

Most rows obey a clean linear rule; a batch of poisoned rows does not. Recover
the flag `NCTF{...}` from the poisoned rows.
