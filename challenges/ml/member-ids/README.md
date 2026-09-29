# member-ids

You are given one file:

- `shadow_eval.npz` with three arrays (same length, one entry per record):
  - `record_id` -- integer id of the record.
  - `loss` -- the model's loss on that record.
  - `tag` -- a single character code attached to the record.

Some records were in the model's training set (members), others were held out.
Recover the flag `NCTF{...}` from the members.
