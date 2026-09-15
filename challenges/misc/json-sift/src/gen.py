#!/usr/bin/env python3
"""Generate telemetry.json for the json-sift challenge.

A large array of event records is emitted. Exactly the records that satisfy
    tag == "delta"  AND  active == true
carry one flag character each in their ``ch`` field; concatenated in ascending
``seq`` order they spell the flag. Every other record is noise, including
plenty of decoys that match only one half of the predicate.
"""

import json
import os
import random

FLAG = "NCTF{jq_pipelines_beat_grep_every_time}"
REGIONS = ["TG", "GH", "BJ", "NG", "CI", "SN"]
TAGS = ["alpha", "beta", "gamma", "delta", "epsilon"]


def main() -> None:
    rng = random.Random(20260914)
    records = []

    # Flag-carrying records: tag=delta AND active=true, seq strictly increasing.
    flag_seqs = sorted(rng.sample(range(1000, 9000), len(FLAG)))
    for seq, ch in zip(flag_seqs, FLAG):
        records.append(
            {
                "seq": seq,
                "region": rng.choice(REGIONS),
                "tag": "delta",
                "active": True,
                "score": rng.randint(0, 500),
                "ch": ch,
            }
        )

    # Noise, including decoys that match only one half of the predicate.
    used = set(flag_seqs)
    while len(records) < 5000:
        seq = rng.randint(1, 99999)
        if seq in used:
            continue
        used.add(seq)
        tag = rng.choice(TAGS)
        active = rng.random() < 0.6
        # Never let a noise record satisfy BOTH halves of the predicate.
        if tag == "delta" and active:
            active = False
        records.append(
            {
                "seq": seq,
                "region": rng.choice(REGIONS),
                "tag": tag,
                "active": active,
                "score": rng.randint(0, 500),
                "ch": rng.choice("abcdefghijklmnopqrstuvwxyz0123456789_{}"),
            }
        )

    rng.shuffle(records)
    out = os.path.join(os.path.dirname(__file__), "..", "telemetry.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(records, fh, separators=(",", ":"))
    print("wrote", os.path.relpath(out), "records:", len(records))


if __name__ == "__main__":
    main()
