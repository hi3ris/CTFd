"""Walk the shipped decision tree and read leaves in path-index order."""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "..", "decision_tree.json")


def collect(node, idx, acc):
    if node["leaf"]:
        acc.append((idx, node["char"]))
        return
    collect(node["left"], idx * 2, acc)
    collect(node["right"], idx * 2 + 1, acc)


def main():
    with open(ART) as f:
        tree = json.load(f)

    leaves = []
    collect(tree, 1, leaves)
    leaves.sort(key=lambda t: t[0])
    print("".join(ch for _, ch in leaves))


if __name__ == "__main__":
    main()
