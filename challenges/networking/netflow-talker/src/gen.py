#!/usr/bin/env python3
"""Generate NetFlow v5-style flow records as CSV.

One source is the "top talker" (by total bytes) -- an exfil host. Each of its
flows encodes one flag character in the destination port: dport = 40000 + ord(c).
Ordering the top talker's flows by their start time and mapping the ports back
to characters yields the flag. Background hosts generate plenty of noise flows
(some also to high ports) but never exceed the exfil host's byte total.

CSV columns: src,dst,sport,dport,proto,packets,octets,first_ms,last_ms
"""

import csv
import os
import random

FLAG = "NCTF{netflow_top_talker_exfil_over_high_ports}"

EXFIL_SRC = "10.4.4.66"
COLLECTOR = "198.51.100.9"
PORT_BASE = 40000


def main():
    rng = random.Random(0x0F10C0DE)
    rows = []

    # exfil host: one flow per flag char, big byte counts, increasing time
    t = 1_000_000
    for i, ch in enumerate(FLAG):
        t += rng.randint(50, 400)
        octets = rng.randint(20000, 40000)
        pkts = rng.randint(20, 60)
        rows.append(
            {
                "src": EXFIL_SRC,
                "dst": COLLECTOR,
                "sport": rng.randint(1024, 65535),
                "dport": PORT_BASE + ord(ch),
                "proto": "tcp",
                "packets": pkts,
                "octets": octets,
                "first_ms": t,
                "last_ms": t + rng.randint(1, 40),
            }
        )

    exfil_total = sum(r["octets"] for r in rows if r["src"] == EXFIL_SRC)

    # background hosts, each kept well under the exfil total
    bg_hosts = ["10.4.4.%d" % n for n in (10, 11, 12, 20, 21, 99)]
    for host in bg_hosts:
        budget = rng.randint(exfil_total // 6, exfil_total // 3)
        used = 0
        while used < budget:
            oc = rng.randint(200, 4000)
            if used + oc > budget:
                break
            used += oc
            tt = rng.randint(900_000, 1_100_000)
            # occasionally use a high port too, as a red herring
            if rng.random() < 0.2:
                dport = PORT_BASE + rng.randint(0, 127)
            else:
                dport = rng.choice([80, 443, 53, 123, 22, 8080])
            rows.append(
                {
                    "src": host,
                    "dst": "%d.%d.%d.%d"
                    % (
                        rng.randint(1, 223),
                        rng.randint(0, 255),
                        rng.randint(0, 255),
                        rng.randint(1, 254),
                    ),
                    "sport": rng.randint(1024, 65535),
                    "dport": dport,
                    "proto": rng.choice(["tcp", "udp"]),
                    "packets": rng.randint(1, 15),
                    "octets": oc,
                    "first_ms": tt,
                    "last_ms": tt + rng.randint(1, 200),
                }
            )

    # sanity: exfil is strictly the top talker
    totals = {}
    for r in rows:
        totals[r["src"]] = totals.get(r["src"], 0) + r["octets"]
    top = max(totals, key=lambda k: totals[k])
    assert top == EXFIL_SRC, (top, totals)

    rng.shuffle(rows)

    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "..", "flows.csv")
    cols = [
        "src",
        "dst",
        "sport",
        "dport",
        "proto",
        "packets",
        "octets",
        "first_ms",
        "last_ms",
    ]
    with open(dest, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(
        "wrote",
        os.path.normpath(dest),
        "rows=%d exfil_total=%d" % (len(rows), exfil_total),
    )


if __name__ == "__main__":
    main()
