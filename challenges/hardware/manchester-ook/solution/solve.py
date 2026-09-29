#!/usr/bin/env python3
"""Reference solver for manchester-ook.

1. Read the 0/1 samples.
2. Recover the half-bit period from the shortest run of a constant level.
3. Reduce the sample stream to one level per half-bit (sample each half-bit's
   centre).
4. Pair half-bits into Manchester bits. Try both pairing offsets and both
   polarity conventions, and both byte-bit offsets, decode MSB-first bytes, and
   keep the interpretation that contains the flag after the 0x7E sync.
"""

import os
import re
import sys


def load(path):
    samples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(int(line))
    return samples


def shortest_run(samples):
    best = None
    run = 1
    for i in range(1, len(samples)):
        if samples[i] == samples[i - 1]:
            run += 1
        else:
            if best is None or run < best:
                best = run
            run = 1
    return best


def half_bit_levels(samples, hb):
    levels = []
    pos = hb // 2
    while pos < len(samples):
        levels.append(samples[pos])
        pos += hb
    return levels


def bits_from_pairs(levels, offset, invert):
    bits = []
    i = offset
    while i + 1 < len(levels):
        a, b = levels[i], levels[i + 1]
        if a == b:  # invalid Manchester symbol -> end of the packet
            break
        # Thomas: (0,1)->1, (1,0)->0 ; invert flips the mapping
        bit = 1 if (a, b) == (0, 1) else 0
        bits.append(bit ^ (1 if invert else 0))
        i += 2
    return bits


def bytes_msb(bits, bit_offset):
    out = bytearray()
    for i in range(bit_offset, len(bits) - 7, 8):
        val = 0
        for b in bits[i : i + 8]:
            val = (val << 1) | b
        out.append(val)
    return bytes(out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, os.pardir, "samples.txt")
    samples = load(path)
    hb = shortest_run(samples)
    levels = half_bit_levels(samples, hb)
    sys.stderr.write(f"half_bit_samples={hb} half_bits={len(levels)}\n")

    pat = re.compile(r"NCTF\{[ -~]*?\}")
    for offset in (0, 1):
        for invert in (False, True):
            bits = bits_from_pairs(levels, offset, invert)
            if not bits:
                continue
            for bit_offset in range(8):
                data = bytes_msb(bits, bit_offset)
                text = data.decode("latin-1")
                m = pat.search(text)
                if m:
                    print(m.group(0))
                    return
    sys.exit("flag not found")


if __name__ == "__main__":
    main()
