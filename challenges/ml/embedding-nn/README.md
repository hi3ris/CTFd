# embedding-nn

You are given one file:

- `embed_table.npz` with three arrays:
  - `embeddings` -- shape `(V, 16)`, one row per token.
  - `token_char` -- shape `(V,)`, the character code for each token row.
  - `queries` -- shape `(L, 16)`, one query vector per flag position.

Each query was derived from a single token's embedding. Decode all `L` queries
in order to recover the flag `NCTF{...}`.
