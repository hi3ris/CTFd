"""Generator for the member-ids challenge (membership inference).

We ship a shadow evaluation table: for each record, its id, the model's per-
record loss, and a character tag. Records the model was TRAINED on (members)
were memorized and have distinctly low loss; held-out records have high loss.

Thresholding the loss separates members from non-members. Reading the member
records' character tags in ascending id order spells the flag.
"""

import numpy as np

FLAG = "NCTF{loss_gap_outs_the_training_set}"


def main():
    rng = np.random.default_rng(424242)

    flag_chars = list(FLAG)
    n_members = len(flag_chars)
    n_nonmembers = 44  # decoys with high loss and random tags

    total = n_members + n_nonmembers
    # Assign ids so members occupy an increasing (but non-contiguous) subset.
    all_ids = rng.permutation(total)
    member_ids = np.sort(all_ids[:n_members])  # ascending -> flag order
    nonmember_ids = all_ids[n_members:]

    ids = []
    losses = []
    tags = []

    # Members: low, memorized loss; tag = the flag char at its position.
    for pos, mid in enumerate(member_ids):
        ids.append(int(mid))
        losses.append(float(rng.uniform(0.01, 0.14)))
        tags.append(flag_chars[pos])

    # Non-members: high loss; random printable decoy tag.
    decoy_alphabet = list("abcdefghijklmnopqrstuvwxyz_{}")
    for nid in nonmember_ids:
        ids.append(int(nid))
        losses.append(float(rng.uniform(0.55, 1.20)))
        tags.append(decoy_alphabet[rng.integers(len(decoy_alphabet))])

    # Shuffle row order so the table is not pre-sorted for the player.
    order = rng.permutation(total)
    ids = np.array(ids)[order]
    losses = np.array(losses)[order]
    tags = np.array([ord(t) for t in tags])[order]

    np.savez(
        "shadow_eval.npz",
        record_id=ids.astype(np.int64),
        loss=losses.astype(np.float64),
        tag=tags.astype(np.int64),
    )
    print("wrote shadow_eval.npz  rows", total, " members", n_members)


if __name__ == "__main__":
    main()
