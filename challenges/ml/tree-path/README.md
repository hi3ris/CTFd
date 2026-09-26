# tree-path

You are given one file:

- `decision_tree.json` -- a binary decision tree.

Node format:

- Internal node: `{"leaf": false, "feature": int, "threshold": float, "left": {...}, "right": {...}}`
- Leaf node: `{"leaf": true, "char": "x"}`

Every leaf holds one character. The characters, read in the correct order,
spell the flag `NCTF{...}`.
