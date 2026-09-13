#!/usr/bin/env python3
"""
Deterministic builder for the misc/timing-channel handout.

    pip install scapy
    python3 gen.py            # -> writes capture.pcap next to this script

What it produces
----------------
A one-directional UDP "heartbeat" capture from an IoT-style status agent
(192.0.2.50) to a collector (198.51.100.10:9999). Every datagram carries a
DELIBERATELY boring, information-free payload: a fixed banner plus a plain
monotonic sequence counter. Nothing in the bytes carries the secret.

The secret lives ENTIRELY in the inter-arrival gaps between consecutive
datagrams:

  * a SHORT gap  (~0.040 s)  encodes bit 0
  * a LONG  gap  (~0.180 s)  encodes bit 1

The two gap populations are drawn with small bounded jitter, so the gap
distribution is clearly BIMODAL with an empty valley around ~0.11 s. A solver
never needs the exact threshold: it can recover it from the histogram (split at
the widest empty band between the two clusters).

Bits are emitted MSB-first, 8 bits per character, concatenated across the whole
capture. N characters -> 8*N gaps -> 8*N + 1 datagrams.

This script keeps NO flag text in the emitted file: the flag exists only as the
timing pattern. gen.py is an author tool and is NOT shipped in `files:`.
"""
import random

from scapy.all import Ether, IP, UDP, Raw, wrpcap

# ---------------------------------------------------------------------------
# The secret. It is encoded purely as timing; it never appears in any payload.
# ---------------------------------------------------------------------------
FLAG = "NCTF{silence_between_beats_speaks}"

# Timing model (seconds). Bounded jitter keeps the two clusters disjoint:
#   bit 0 -> [0.032, 0.048]      bit 1 -> [0.172, 0.188]
# Valley (~0.11 s) is wide and empty, so the split is recoverable from data.
GAP0 = 0.040
GAP1 = 0.180
JITTER = 0.008

# Capture cosmetics
SRC_IP = "192.0.2.50"
DST_IP = "198.51.100.10"
SRC_MAC = "02:00:00:00:00:50"
DST_MAC = "02:00:00:00:00:0a"
SRC_PORT = 48213
DST_PORT = 9999
T0 = 1_726_000_000.0  # arbitrary fixed epoch for determinism
BANNER = b"agent-hb v1 status=online node=edge-07"

SEED = 0xC0FFEE


def bits_of(text: str):
    for ch in text:
        for i in range(7, -1, -1):
            yield (ord(ch) >> i) & 1


def main():
    rng = random.Random(SEED)
    bits = list(bits_of(FLAG))

    packets = []
    t = T0
    seq = 0

    def make_packet(ts: float, n: int):
        # Boring, information-free payload: fixed banner + monotonic counter.
        payload = BANNER + b" seq=%d\n" % n
        pkt = (Ether(src=SRC_MAC, dst=DST_MAC) /
               IP(src=SRC_IP, dst=DST_IP) /
               UDP(sport=SRC_PORT, dport=DST_PORT) /
               Raw(load=payload))
        pkt.time = ts
        return pkt

    # First datagram: no preceding gap, so it carries no bit.
    packets.append(make_packet(t, seq))
    seq += 1

    # Each subsequent datagram's preceding gap encodes exactly one bit.
    for b in bits:
        base = GAP1 if b else GAP0
        gap = base + rng.uniform(-JITTER, JITTER)
        t += gap
        packets.append(make_packet(t, seq))
        seq += 1

    wrpcap("capture.pcap", packets)
    print("[*] flag encoded          :", FLAG)
    print("[*] bits (gaps)           :", len(bits))
    print("[*] datagrams written     :", len(packets))
    print("[*] capture.pcap duration :", round(packets[-1].time - packets[0].time, 3), "s")


if __name__ == "__main__":
    main()
