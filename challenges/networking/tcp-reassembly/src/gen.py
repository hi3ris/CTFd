#!/usr/bin/env python3
"""Generate out-of-order TCP segments (JSON) that reassemble into the flag.

Twists that make plain sorting fail:
  * absolute 32-bit sequence numbers with an ISN near 2**32, so seq WRAPS and
    offsets must be computed modulo 2**32;
  * segments delivered out of order;
  * exact retransmissions (duplicate seq + data) as noise;
  * partially overlapping retransmissions carrying identical overlap bytes.

A SYN segment carries the ISN. Payload bytes are hex-encoded.
"""

import json
import os
import random

FLAG = b"NCTF{tcp_reassembly_by_absolute_seq_with_wraparound_and_dedup}"

MOD = 1 << 32
ISN = 0xFFFFFF80  # close to the wrap boundary


def main():
    rng = random.Random(0x7C9A55)

    # Non-overlapping base tiling of the flag.
    base = []
    i = 0
    while i < len(FLAG):
        n = rng.randint(3, 6)
        base.append((i, FLAG[i : i + n]))
        i += n

    segs = []

    def seq_for(offset):
        return (ISN + 1 + offset) % MOD

    # SYN
    segs.append({"seq": ISN, "flags": ["SYN"], "data": ""})

    # base data segments
    for off, chunk in base:
        segs.append({"seq": seq_for(off), "flags": ["ACK"], "data": chunk.hex()})

    # exact retransmissions of a few segments (noise)
    for off, chunk in rng.sample(base, k=max(2, len(base) // 4)):
        segs.append({"seq": seq_for(off), "flags": ["ACK"], "data": chunk.hex()})

    # overlapping retransmission: merge two adjacent base chunks into one bigger
    # segment (identical overlap bytes) to exercise offset-based placement
    for _ in range(3):
        j = rng.randrange(len(base) - 1)
        off = base[j][0]
        merged = base[j][1] + base[j + 1][1]
        segs.append({"seq": seq_for(off), "flags": ["ACK"], "data": merged.hex()})

    # FIN
    segs.append({"seq": seq_for(len(FLAG)), "flags": ["FIN", "ACK"], "data": ""})

    rng.shuffle(segs)

    doc = {
        "note": "one TCP direction; absolute 32-bit seq numbers; ISN is in the"
        " SYN segment; payload is hex; reassemble by byte offset.",
        "segments": segs,
    }
    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "..", "segments.json")
    with open(dest, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    print(
        "wrote",
        os.path.normpath(dest),
        "segments=%d flaglen=%d" % (len(segs), len(FLAG)),
    )


if __name__ == "__main__":
    main()
