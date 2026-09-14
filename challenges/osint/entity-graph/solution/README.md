# entity-graph — writeup

**Category:** osint · **Difficulty:** medium
**Flag:** `NCTF{maltego_pivot_kossivi_agbeko_unmasked}`

## Summary

A Maltego-style investigation graph is shipped as two CSVs. Pivoting from the
seed persona along verified links only reaches exactly one real identity, whose
dossier note is the flag.

## Technique

Link analysis / graph pivoting with edge-trust filtering. The trap is that the
graph mixes analyst-confirmed edges with speculative ones. Following speculative
edges (`mentions`, `follows`, `similar_name`) reaches decoy `person` nodes,
including a decoy flag `NCTF{wrong_pivot_speculative_link}`.

## Step by step

1. Load `nodes.csv` (id, type, label, value, note) and `edges.csv`
   (src, dst, relation).
2. Keep only the VERIFIED relations: `same_email`, `same_phone`, `same_device`,
   `owns_wallet`, `registered_by`, `confirmed_aka`. Treat them as undirected.
3. BFS from the seed node `h_seed` (`z3ro_237`). The verified chain is:
   `z3ro_237 → z3r0.lome@protomail.tg → cobra_lome → +22890114477 →
IMEI 356938035643809 → BTC wallet → mining-togo.tg → Kossivi Agbeko`.
4. Exactly one `person` node is reachable: `Kossivi Agbeko`. Its `note` column
   is the flag.

Run `python3 solution/solve.py` to reproduce.

## Flag

`NCTF{maltego_pivot_kossivi_agbeko_unmasked}`
