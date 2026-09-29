#!/usr/bin/env python3
"""Reference solver for uart-capture.

Decode the UART data line (`d0_uart`) from the logic-analyzer CSV:

1. Read the samples and the sample period from the `time_ns` column.
2. Recover the baud rate from the shortest run of constant level on the line
   (one bit time) -> samples-per-bit.
3. For every falling edge from idle (1 -> 0) treat it as a start bit, sample
   the middle of each of the following 8 bit cells (LSB-first), verify the
   stop bit is high, and rebuild the byte.
4. Concatenate the bytes into the ASCII payload = the flag.
"""

import csv
import os
import sys


def load(path):
    times, line = [], []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            times.append(int(row["time_ns"]))
            line.append(int(row["d0_uart"]))
    dt = times[1] - times[0]
    sample_rate = 1_000_000_000 // dt
    return line, sample_rate


def shortest_run(line):
    best = None
    run = 1
    for i in range(1, len(line)):
        if line[i] == line[i - 1]:
            run += 1
        else:
            if best is None or run < best:
                best = run
            run = 1
    return best


def decode(line, spb):
    out = bytearray()
    i = 0
    n = len(line)
    while i < n - 1:
        # find a falling edge into a start bit while idle-high
        if line[i] == 1 and line[i + 1] == 0:
            start = i + 1

            # sample centre of each data bit (bit 0 is the start bit)
            def center(bit_index):
                pos = start + int((bit_index + 0.5) * spb)
                return line[pos] if pos < n else 1

            byte = 0
            for b in range(8):
                byte |= center(1 + b) << b  # LSB first, skip start bit
            stop = center(9)
            if stop == 1:
                out.append(byte)
            i = start + 10 * spb  # advance past this frame
        else:
            i += 1
    return bytes(out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, os.pardir, "capture.csv")
    line, sample_rate = load(path)
    spb = shortest_run(line)
    baud = sample_rate // spb
    payload = decode(line, spb)
    text = payload.decode("ascii", "replace")
    sys.stderr.write(f"sample_rate={sample_rate} spb={spb} baud={baud}\n")
    print(text)


if __name__ == "__main__":
    main()
