#!/usr/bin/env python3
"""
Reference solver for forensics-dns-exfil.

    pip install scapy
    python3 solve.py ../capture.pcap

Steps:
  1. Read all DNS *queries* (qr == 0) whose name ends with the exfil domain.
  2. The 'init.<ALPHABET>....' query announces the custom base32 alphabet.
  3. Every other exfil query is '<seq3>.<chunk>....'; collect {seq: chunk},
     de-duplicating retransmissions, sort by seq, concatenate ALL chunks.
  4. Decode the single concatenated stream with the custom alphabet
     (MSB-first 5-bit packing, no padding).
  5. Print the note; the recovery_token line is the flag.

The A-record beacon to sync.telemetry-cdn.net is a decoy: it is standard base32
and decodes to a fake, flag-shaped IDS-signature string. The brief says the real
channel is DNS TXT, so we ignore non-TXT / other-domain traffic.
"""
import re
import sys

from scapy.all import rdpcap, DNS, DNSQR

EXFIL_SUFFIX = "x.acme-updates.net"
RFC4648 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def b32_custom_decode(s: str, alphabet: str) -> bytes:
    idx = {c: i for i, c in enumerate(alphabet)}
    bits = "".join(f"{idx[c]:05b}" for c in s)
    n = len(bits) // 8
    return bytes(int(bits[i * 8:i * 8 + 8], 2) for i in range(n))


def main(path):
    pkts = rdpcap(path)
    alphabet = None
    chunks = {}  # seq(int) -> chunk(str)

    for p in pkts:
        if not p.haslayer(DNS) or not p.haslayer(DNSQR):
            continue
        dns = p[DNS]
        if dns.qr != 0:
            continue  # queries only
        qd = p[DNSQR]  # exactly one question in each query here
        # TXT queries only (qtype 16)
        if getattr(qd, "qtype", None) != 16:
            continue
        qname = qd.qname.decode(errors="replace").rstrip(".")
        if not qname.endswith(EXFIL_SUFFIX):
            continue
        label0 = qname.split(".", 2)  # [first, second, rest]
        first = label0[0]
        if first == "init":
            alphabet = label0[1]
            continue
        if re.fullmatch(r"\d{3}", first):
            seq = int(first)
            chunks[seq] = label0[1]  # de-dupes retransmissions automatically

    if alphabet is None:
        sys.exit("[!] no init/alphabet query found")
    if sorted(alphabet) != sorted(RFC4648):
        sys.exit(f"[!] announced alphabet is not a base32 permutation: {alphabet}")

    print(f"[*] custom alphabet : {alphabet}")
    print(f"[*] distinct chunks : {len(chunks)}  (seq 0..{max(chunks)})")

    stream = "".join(chunks[i] for i in sorted(chunks))
    data = b32_custom_decode(stream, alphabet)

    print("[*] decoded note:\n")
    sys.stdout.write(data.decode(errors="replace"))
    m = re.search(r"CTF\{[^}]+\}", data.decode(errors="replace"))
    print("\n[+] FLAG:", m.group(0) if m else "<not found>")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../capture.pcap")
