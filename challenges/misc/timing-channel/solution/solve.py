#!/usr/bin/env python3
"""
Reference solver for misc/timing-channel.

    pip install scapy
    python3 solve.py ../capture.pcap

Idea
----
The datagram PAYLOADS are all identical apart from a plain monotonic `seq=`
counter, so the bytes carry nothing. The signal is in *when* each datagram
arrives.

Steps:
  1. Read every datagram's capture timestamp (in order) and take the
     inter-arrival gaps between consecutive datagrams.
  2. The gaps form two tight clusters (a bimodal distribution) with an empty
     valley in between. Recover the split WITHOUT hardcoding it: sort the gaps
     and cut at the widest empty band -> everything below = short, above = long.
  3. short gap -> bit 0, long gap -> bit 1, in capture order.
  4. Pack the bitstream MSB-first, 8 bits per byte, into ASCII.
  5. The decoded text is the flag.
"""
import sys

from scapy.all import rdpcap, UDP


def gaps_from_pcap(path):
    pkts = rdpcap(path)
    times = [float(p.time) for p in pkts if p.haslayer(UDP)]
    times.sort()  # arrival order
    return [b - a for a, b in zip(times, times[1:])]


def infer_threshold(gaps):
    """Split the bimodal gap distribution at its widest empty band."""
    s = sorted(gaps)
    best_lo, best_hi, best_span = s[0], s[0], -1.0
    for a, b in zip(s, s[1:]):
        if b - a > best_span:
            best_span, best_lo, best_hi = b - a, a, b
    return (best_lo + best_hi) / 2.0


def main(path):
    gaps = gaps_from_pcap(path)
    if not gaps:
        sys.exit("[!] no UDP datagrams found")

    thr = infer_threshold(gaps)
    lo = [g for g in gaps if g < thr]
    hi = [g for g in gaps if g >= thr]
    print(f"[*] gaps            : {len(gaps)}")
    print(f"[*] inferred split  : {thr*1000:.1f} ms "
          f"(short~{sum(lo)/len(lo)*1000:.0f}ms x{len(lo)}, "
          f"long~{sum(hi)/len(hi)*1000:.0f}ms x{len(hi)})")

    bitstr = "".join("1" if g >= thr else "0" for g in gaps)
    n = len(bitstr) // 8
    out = bytes(int(bitstr[i * 8:i * 8 + 8], 2) for i in range(n))
    text = out.decode(errors="replace")
    print("[*] decoded (MSB-first, 8 bits/char):")
    print("   ", text)

    if text.startswith("NCTF{") and text.endswith("}"):
        print("[+] FLAG:", text)
    else:
        # Fallback: if bit polarity were reversed, try the complement.
        alt = "".join("0" if c == "1" else "1" for c in bitstr)
        m = len(alt) // 8
        alt_txt = bytes(int(alt[i*8:i*8+8], 2) for i in range(m)).decode(errors="replace")
        print("[?] complement    :", alt_txt)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../capture.pcap")
