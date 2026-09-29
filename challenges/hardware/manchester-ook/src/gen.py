#!/usr/bin/env python3
"""Generate an OOK (on-off keying) sample capture of a Manchester-coded packet.

`samples.txt` is one integer (0 or 1) per line: the demodulated RF envelope,
oversampled at HB samples per half-bit. Each data bit is two half-bits
(Manchester / G. E. Thomas convention):

  bit 1 -> low then high   (half-bits 0,1)
  bit 0 -> high then low   (half-bits 1,0)

Packet: a run-in preamble (alternating bits) to establish timing, a sync byte
0x7E, then the flag as bytes MSB-first.
"""

import os

HB = 5  # samples per half-bit
SYNC = 0x7E
FLAG = b"NCTF{manchester_ook_diff_decoded}"


def bit_to_halfbits(bit):
    # Thomas convention: 1 -> (0,1), 0 -> (1,0)
    return (0, 1) if bit else (1, 0)


def encode_bits(bits):
    samples = []
    for bit in bits:
        for hb in bit_to_halfbits(bit):
            samples += [hb] * HB
    return samples


def byte_bits(byte):
    return [(byte >> i) & 1 for i in range(7, -1, -1)]  # MSB first


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, os.pardir, "samples.txt")

    bits = []
    bits += [1, 0] * 16  # preamble
    bits += byte_bits(SYNC)  # sync
    for b in FLAG:
        bits += byte_bits(b)

    samples = encode_bits(bits)
    samples += [0] * (HB * 4)  # trailing silence

    with open(out, "w") as f:
        f.write("\n".join(str(s) for s in samples) + "\n")

    print("wrote", os.path.abspath(out), "samples:", len(samples))


if __name__ == "__main__":
    main()
