"""Identify memorized members by their low loss and read the flag."""

import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "..", "shadow_eval.npz")


def main():
    data = np.load(ART)
    ids = data["record_id"]
    loss = data["loss"]
    tag = data["tag"]

    # The loss histogram is bimodal; members sit well below the gap.
    threshold = 0.4
    members = loss < threshold

    member_ids = ids[members]
    member_tags = tag[members]

    # Read member tags in ascending id order.
    order = np.argsort(member_ids)
    flag = "".join(chr(int(t)) for t in member_tags[order])
    print(flag)


if __name__ == "__main__":
    main()
