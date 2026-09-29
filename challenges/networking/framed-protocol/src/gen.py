#!/usr/bin/env python3
"""Generate a hex byte stream of a custom application protocol.

Wire frame (all multi-byte fields big-endian):

    +------+------+------+----------+-----------------+------+
    | SOF  |  OP  | SEQ  |  LEN(2)  | PAYLOAD (LEN B) | CRC  |
    +------+------+------+----------+-----------------+------+
      0xAA   1B     1B      2B          LEN bytes        1B

    CRC = XOR of every byte from OP through the last payload byte.

Opcodes: 0x10 DATA, 0x20 NOISE, 0x30 END. DATA payloads are chunks of the flag.
Frames must be walked by LEN (payloads may themselves contain 0xAA), CRC-checked
(corrupt frames are dropped), then DATA frames ordered by SEQ and concatenated.
"""

import os
import random

FLAG = b"NCTF{custom_framing_len_prefixed_crc_checked_reassembly}"

SOF = 0xAA
OP_DATA = 0x10
OP_NOISE = 0x20
OP_END = 0x30


def crc(body):
    x = 0
    for b in body:
        x ^= b
    return x


def frame(op, seq, payload, corrupt=False):
    ln = len(payload)
    body = bytes([op, seq, (ln >> 8) & 0xFF, ln & 0xFF]) + payload
    c = crc(body)
    if corrupt:
        c ^= 0x5A  # break the CRC on purpose
    return bytes([SOF]) + body + bytes([c])


def main():
    rng = random.Random(0xF3A3E)

    # split flag into chunks and assign sequence numbers
    chunks = []
    i = 0
    seq = 0
    seqs = []
    while i < len(FLAG):
        n = rng.randint(3, 7)
        chunks.append((seq, FLAG[i : i + n]))
        seqs.append(seq)
        i += n
        seq += 1

    frames = []
    # good DATA frames, shuffled order on the wire
    data_frames = [(s, frame(OP_DATA, s, p)) for (s, p) in chunks]
    rng.shuffle(data_frames)

    def noise():
        payload = bytes(rng.randint(0, 255) for _ in range(rng.randint(2, 10)))
        return frame(OP_NOISE, rng.randint(0, 255), payload)

    def corrupt_data():
        # looks like DATA but bad CRC and bogus payload -> must be dropped
        payload = b"XX" + bytes(rng.randint(0, 255) for _ in range(rng.randint(2, 5)))
        return frame(OP_DATA, rng.randint(200, 255), payload, corrupt=True)

    for _, fr in data_frames:
        if rng.random() < 0.6:
            frames.append(noise())
        if rng.random() < 0.25:
            frames.append(corrupt_data())
        frames.append(fr)
    frames.append(noise())
    frames.append(frame(OP_END, 0, b""))

    stream = b"".join(frames)
    hexstr = stream.hex()
    # wrap to 64 hex chars (32 bytes) per line for readability
    lines = [hexstr[j : j + 64] for j in range(0, len(hexstr), 64)]

    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "..", "stream.hex")
    with open(dest, "w") as f:
        f.write("\n".join(lines))
        f.write("\n")
    print(
        "wrote",
        os.path.normpath(dest),
        "bytes=%d frames=%d" % (len(stream), len(frames)),
    )


if __name__ == "__main__":
    main()
