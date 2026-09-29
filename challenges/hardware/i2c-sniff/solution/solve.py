#!/usr/bin/env python3
"""Reference solver for i2c-sniff.

Decode I2C from the SCL/SDA capture:

1. Collapse the oversampled rows to edge events.
2. Detect START (SDA 1->0 while SCL high) and STOP (SDA 0->1 while SCL high).
3. Between START and STOP, sample SDA on each SCL rising edge; group into
   9-bit units (8 data bits MSB-first + 1 ACK bit).
4. First byte is (address<<1 | R/W); the remaining data bytes are the flag.
"""

import csv
import os
import sys


def load(path):
    scl, sda = [], []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            scl.append(int(row["SCL"]))
            sda.append(int(row["SDA"]))
    return scl, sda


def decode(scl, sda):
    bytes_out = []
    bits = []
    active = False
    n = len(scl)
    for i in range(1, n):
        scl_prev, scl_cur = scl[i - 1], scl[i]
        sda_prev, sda_cur = sda[i - 1], sda[i]
        # START / STOP: SDA edge while SCL held high
        if scl_prev == 1 and scl_cur == 1:
            if sda_prev == 1 and sda_cur == 0:  # START
                active = True
                bits = []
                continue
            if sda_prev == 0 and sda_cur == 1:  # STOP
                active = False
                continue
        # data: latch SDA on SCL rising edge
        if active and scl_prev == 0 and scl_cur == 1:
            bits.append(sda_cur)
            if len(bits) == 9:  # 8 data + ACK
                val = 0
                for b in bits[:8]:
                    val = (val << 1) | b
                bytes_out.append(val)
                bits = []
    return bytes_out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, os.pardir, "i2c_capture.csv")
    scl, sda = load(path)
    data = decode(scl, sda)
    addr = data[0] >> 1
    rw = "W" if (data[0] & 1) == 0 else "R"
    sys.stderr.write(f"slave_addr=0x{addr:02x} rw={rw}\n")
    payload = bytes(data[1:]).decode("ascii", "replace")
    print(payload)


if __name__ == "__main__":
    main()
