# entity-graph — writeup

**Category:** osint · **Difficulty:** easy
**Flag:** `NCTF{79dcf5d4d250f13b9940549a}`

## Summary

A Maltego-style investigation graph is shipped as two CSVs. Pivoting from the
seed persona along verified links only reaches exactly one real identity. The
flag is **not** written in the graph — it is derived from the verified pivot
path, so you have to actually traverse the graph to produce it.

## Technique

Link analysis / graph pivoting with edge-trust filtering, then a keyed HMAC over
the recovered path. The trap is that the graph mixes analyst-confirmed edges
with speculative ones. Following speculative edges (`mentions`, `follows`,
`similar_name`) reaches decoy `person` nodes, including a decoy flag
`NCTF{wrong_pivot_speculative_link}` stored verbatim in `nodes.csv` — grepping
for `NCTF{` gives you only that wrong answer.

## Step by step

1. Load `nodes.csv` (id, type, label, value, note) and `edges.csv`
   (src, dst, relation).
2. Keep only the VERIFIED relations: `same_email`, `same_phone`, `same_device`,
   `owns_wallet`, `registered_by`, `confirmed_aka`. Treat them as undirected.
3. BFS from the seed node `h_seed` (`z3ro_237`) and reconstruct the ordered path
   to the single reachable `person`. The verified chain is:
   `z3ro_237 → z3r0.lome@protomail.tg → cobra_lome → +22890114477 →
IMEI 356938035643809 → BTC wallet → mining-togo.tg → Kossivi Agbeko`.
4. Derive the flag from that pivot. Join the `value` of every node on the path
   (seed → target) with `|`, then compute
   `HMAC-SHA256(key = target label "Kossivi Agbeko", msg = joined values)` and
   take the first 24 hex digits: `NCTF{<hex>}`. Any speculative detour changes
   the reachable set / path and yields the wrong digest.

Run `python3 solution/solve.py` to reproduce.

## Flag

`NCTF{79dcf5d4d250f13b9940549a}`
