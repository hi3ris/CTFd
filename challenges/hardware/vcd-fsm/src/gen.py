#!/usr/bin/env python3
"""Generate a VCD (Value Change Dump) waveform of a Moore state machine.

Signals:
  clk        - 1-bit clock (period 10 ticks, rising edge every 10)
  state[3:0] - the FSM's current state index (0,1,2,... wrapping)
  dout[7:0]  - the Moore output: one ASCII byte, updated at each rising edge

The flag is the sequence of `dout` bytes latched on the rising edges of `clk`.
An extra `noise[7:0]` signal wiggles between edges as a decoy; it is only ever
valid to read `dout` at the clock's rising edge.
"""

import os

FLAG = "NCTF{vcd_moore_fsm_output_trace}"


def bits(value, width):
    return format(value & ((1 << width) - 1), "0{}b".format(width))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, os.pardir, "trace.vcd")

    ids = {"clk": "!", "state": '"', "dout": "#", "noise": "$"}
    payload = FLAG.encode()

    lines = []
    lines.append("$date Mon Jan 1 00:00:00 2024 $end")
    lines.append("$version gen.py fsm dumper $end")
    lines.append("$timescale 1ns $end")
    lines.append("$scope module fsm $end")
    lines.append(f"$var wire 1 {ids['clk']} clk $end")
    lines.append(f"$var reg 4 {ids['state']} state [3:0] $end")
    lines.append(f"$var reg 8 {ids['dout']} dout [7:0] $end")
    lines.append(f"$var reg 8 {ids['noise']} noise [7:0] $end")
    lines.append("$upscope $end")
    lines.append("$enddefinitions $end")

    # initial values at t=0
    lines.append("#0")
    lines.append("$dumpvars")
    lines.append(f"0{ids['clk']}")
    lines.append(f"b0000 {ids['state']}")
    lines.append(f"b00000000 {ids['dout']}")
    lines.append(f"b00000000 {ids['noise']}")
    lines.append("$end")

    period = 10
    lfsr = 0xA5
    t = 0
    for i, byte in enumerate(payload):
        # falling half: clk goes low, noise wiggles (decoy)
        t_low = t + period // 2
        lfsr = ((lfsr << 1) ^ (0x1D if (lfsr & 0x80) else 0)) & 0xFF
        lines.append(f"#{t_low}")
        lines.append(f"0{ids['clk']}")
        lines.append(f"b{bits(lfsr, 8)} {ids['noise']}")
        # rising edge at t+period: clk high, state advances, dout = payload byte
        t += period
        lines.append(f"#{t}")
        lines.append(f"1{ids['clk']}")
        lines.append(f"b{bits(i + 1, 4)} {ids['state']}")
        lines.append(f"b{bits(byte, 8)} {ids['dout']}")

    lines.append(f"#{t + period}")

    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")

    print("wrote", os.path.abspath(out), "bytes:", len(payload))


if __name__ == "__main__":
    main()
