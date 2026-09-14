#!/usr/bin/env python3
"""Reference solver for spi-eeprom.

Decode SPI mode 0 from the 4-channel capture:

1. While CS is low, find each rising edge of CLK.
2. On every rising edge latch MOSI and MISO (MSB-first, 8 bits per byte).
3. The MOSI stream is the command: opcode 0x03, then a 16-bit address.
4. The MISO stream during the data phase is the EEPROM's returned bytes = flag.
"""

import csv
import os
import sys


def load(path):
    cs, clk, mosi, miso = [], [], [], []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            cs.append(int(row["CS"]))
            clk.append(int(row["CLK"]))
            mosi.append(int(row["MOSI"]))
            miso.append(int(row["MISO"]))
    return cs, clk, mosi, miso


def sample_bits(cs, clk, line):
    """Return the bit latched on each CLK rising edge while CS is low."""
    bits = []
    for i in range(1, len(clk)):
        if cs[i] == 0 and clk[i - 1] == 0 and clk[i] == 1:
            bits.append(line[i])
    return bits


def pack_msb(bits):
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for b in bits[i : i + 8]:
            byte = (byte << 1) | b
        out.append(byte)
    return bytes(out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, os.pardir, "spi_capture.csv")
    cs, clk, mosi, miso = load(path)

    mosi_bytes = pack_msb(sample_bits(cs, clk, mosi))
    miso_bytes = pack_msb(sample_bits(cs, clk, miso))

    opcode = mosi_bytes[0]
    addr = (mosi_bytes[1] << 8) | mosi_bytes[2]
    sys.stderr.write(f"opcode=0x{opcode:02x} addr=0x{addr:04x}\n")

    # data phase begins after opcode(1) + address(2) = 3 command bytes
    flag = miso_bytes[3:].decode("ascii", "replace")
    print(flag)


if __name__ == "__main__":
    main()
