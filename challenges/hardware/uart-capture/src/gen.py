#!/usr/bin/env python3
"""Generate a logic-analyzer capture (CSV) of a single UART line.

The capture is a uniformly-sampled digital recording of one data line plus a
free-running reference clock (a decoy channel that carries no framing). The
UART line is idle-high, 8N1 (1 start bit low, 8 data bits LSB-first, 1 stop
bit high), no parity. The flag is the transmitted ASCII payload.

Sample rate: 1_000_000 Hz  ->  1 sample per microsecond (dt = 1000 ns).
Baud rate:   125000        ->  exactly 8 samples per bit.
"""

import csv
import os

SAMPLE_RATE = 1_000_000
BAUD = 125_000
SPB = SAMPLE_RATE // BAUD  # samples per bit = 8
DT_NS = 1_000_000_000 // SAMPLE_RATE  # 1000 ns
CLK_HALF = 3  # decoy clock: 3-sample half period, unrelated to the UART timing

FLAG = "NCTF{uart_8n1_lsb_first_125k}"


def uart_bits(payload):
    """Yield the idle-high UART line as a list of per-sample levels."""
    levels = []
    # leading idle
    levels += [1] * (SPB * 12)
    for byte in payload:
        frame = [0]  # start bit
        for i in range(8):  # 8 data bits, LSB first
            frame.append((byte >> i) & 1)
        frame.append(1)  # stop bit
        for bit in frame:
            levels += [bit] * SPB
        levels += [1] * (SPB * 2)  # inter-byte idle
    levels += [1] * (SPB * 12)  # trailing idle
    return levels


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, os.pardir, "capture.csv")

    data = uart_bits(FLAG.encode())
    n = len(data)

    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_ns", "d0_uart", "d1_refclk"])
        for i in range(n):
            clk = (i // CLK_HALF) % 2
            w.writerow([i * DT_NS, data[i], clk])

    print("wrote", os.path.abspath(out), "samples:", n)


if __name__ == "__main__":
    main()
