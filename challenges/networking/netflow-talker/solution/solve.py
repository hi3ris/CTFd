#!/usr/bin/env python3
"""Find the top talker by total bytes, decode its high-port flows into the flag."""

import csv
import os

PORT_BASE = 40000


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    rows = list(csv.DictReader(open(os.path.join(here, "..", "flows.csv"))))
    for r in rows:
        r["octets"] = int(r["octets"])
        r["dport"] = int(r["dport"])
        r["first_ms"] = int(r["first_ms"])

    totals = {}
    for r in rows:
        totals[r["src"]] = totals.get(r["src"], 0) + r["octets"]
    top = max(totals, key=lambda k: totals[k])

    flows = [r for r in rows if r["src"] == top]
    flows.sort(key=lambda r: r["first_ms"])
    flag = "".join(chr(r["dport"] - PORT_BASE) for r in flows)
    print(flag)


if __name__ == "__main__":
    main()
