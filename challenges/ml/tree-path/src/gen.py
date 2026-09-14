"""Generator for the tree-path challenge (decision-tree rule extraction).

We ship a trained binary decision tree as JSON. Internal nodes split on a
feature/threshold; leaves carry a single character. Each leaf has a canonical
position given by its root-to-leaf path (start index 1; go left => idx*2, go
right => idx*2+1). Listing the leaf characters in ascending path-index order
spells the flag. The tree's JSON stores children in randomized order so the
player must actually walk the paths, not read the file top to bottom.
"""

import json
import random

FLAG = "NCTF{gini_split_leaks_the_leaf_path}"


def build(rng, n_leaves):
    """Build a random binary tree with exactly n_leaves leaves."""
    if n_leaves == 1:
        return {"leaf": True}
    left_leaves = rng.randint(1, n_leaves - 1)
    right_leaves = n_leaves - left_leaves
    return {
        "leaf": False,
        "feature": rng.randint(0, 7),
        "threshold": round(rng.uniform(-1.0, 1.0), 3),
        "left": build(rng, left_leaves),
        "right": build(rng, right_leaves),
    }


def collect_leaves(node, idx, acc):
    """Record (path_index, leaf_node) for every leaf."""
    if node["leaf"]:
        acc.append((idx, node))
        return
    collect_leaves(node["left"], idx * 2, acc)
    collect_leaves(node["right"], idx * 2 + 1, acc)


def main():
    rng = random.Random(20240914)

    tree = build(rng, len(FLAG))

    leaves = []
    collect_leaves(tree, 1, leaves)
    leaves.sort(key=lambda t: t[0])  # canonical path-index order

    for (_, leaf), ch in zip(leaves, FLAG):
        leaf["char"] = ch

    with open("decision_tree.json", "w") as f:
        json.dump(tree, f, indent=2)
    print("wrote decision_tree.json  leaves", len(leaves))


if __name__ == "__main__":
    main()
