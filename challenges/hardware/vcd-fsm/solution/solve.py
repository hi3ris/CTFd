#!/usr/bin/env python3
"""Reference solver for vcd-fsm.

Parse the VCD, replay value changes over time, and sample the `dout` vector on
every rising edge of `clk`. Those bytes are the flag.
"""

import os
import sys


def parse_vcd(path):
    name_to_id = {}
    changes = []  # list of (time, id, value)
    in_defs = True
    cur_time = 0
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if in_defs:
                if line.startswith("$var"):
                    parts = line.split()
                    # $var <type> <width> <id> <name> ... $end
                    ident = parts[3]
                    name = parts[4]
                    name_to_id[name] = ident
                elif line.startswith("$enddefinitions"):
                    in_defs = False
                continue
            if line.startswith("$dumpvars") or line == "$end":
                continue
            if line.startswith("#"):
                cur_time = int(line[1:])
            elif line[0] in "01xzXZ":  # scalar change: <val><id>
                val = line[0]
                ident = line[1:]
                changes.append((cur_time, ident, val))
            elif line[0] in "bB":  # vector change: b<bits> <id>
                token, ident = line.split()
                changes.append((cur_time, ident, token[1:]))
    return name_to_id, changes


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, os.pardir, "trace.vcd")

    name_to_id, changes = parse_vcd(path)
    clk_id = name_to_id["clk"]
    dout_id = name_to_id["dout"]

    # replay in time order; state holds current value of each id
    state = {}
    out = bytearray()
    prev_clk = "0"
    # group changes by time so simultaneous edges settle before we sample
    changes.sort(key=lambda c: c[0])
    i = 0
    n = len(changes)
    while i < n:
        t = changes[i][0]
        while i < n and changes[i][0] == t:
            _, ident, val = changes[i]
            state[ident] = val
            i += 1
        clk = state.get(clk_id, "0")
        if prev_clk == "0" and clk == "1":  # rising edge
            bitstr = state.get(dout_id, "0")
            out.append(int(bitstr, 2))
        prev_clk = clk

    print(bytes(out).decode("ascii", "replace"))


if __name__ == "__main__":
    main()
