#!/usr/bin/env python3
"""Generate an SPI bus capture (CSV) of an EEPROM read transaction.

Four channels are recorded, oversampled ~4x the SPI clock:

  CS   - chip select, active LOW
  CLK  - SPI clock, SPI mode 0 (CPOL=0, CPHA=0): sample on the RISING edge
  MOSI - master out (command + address)
  MISO - slave out (the returned data bytes)

The master issues a READ (opcode 0x03) at a 16-bit address, then clocks out
zeros while the EEPROM shifts the stored bytes back on MISO, MSB-first. The
flag is the ASCII content the EEPROM returns.
"""

import csv
import os

OVERSAMPLE = 4  # samples per SPI clock half-period
FLAG = "NCTF{spi_mode0_msb_first_eeprom}"
READ_OPCODE = 0x03
ADDR = 0x0100


class Bus:
    def __init__(self):
        self.rows = []  # (cs, clk, mosi, miso)
        self.cs = 1
        self.clk = 0
        self.mosi = 0
        self.miso = 0

    def emit(self, n=1):
        for _ in range(n):
            self.rows.append((self.cs, self.clk, self.mosi, self.miso))

    def xfer_byte(self, out_byte, in_byte):
        """Shift 8 bits MSB-first, mode 0: set data while CLK low, latch on rise."""
        for i in range(7, -1, -1):
            self.mosi = (out_byte >> i) & 1
            self.miso = (in_byte >> i) & 1
            self.clk = 0  # data set-up phase
            self.emit(OVERSAMPLE)
            self.clk = 1  # rising edge -> sampled here
            self.emit(OVERSAMPLE)
        self.clk = 0
        self.emit(OVERSAMPLE)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, os.pardir, "spi_capture.csv")

    bus = Bus()
    bus.emit(8)  # idle, CS high
    bus.cs = 0  # select
    bus.emit(4)

    payload = FLAG.encode()
    # command phase: opcode + 16-bit address (MISO undefined -> 0)
    bus.xfer_byte(READ_OPCODE, 0x00)
    bus.xfer_byte((ADDR >> 8) & 0xFF, 0x00)
    bus.xfer_byte(ADDR & 0xFF, 0x00)
    # data phase: master clocks 0x00, EEPROM returns payload on MISO
    for b in payload:
        bus.xfer_byte(0x00, b)

    bus.cs = 1  # deselect
    bus.emit(8)

    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample", "CS", "CLK", "MOSI", "MISO"])
        for i, (cs, clk, mosi, miso) in enumerate(bus.rows):
            w.writerow([i, cs, clk, mosi, miso])

    print("wrote", os.path.abspath(out), "samples:", len(bus.rows))


if __name__ == "__main__":
    main()
