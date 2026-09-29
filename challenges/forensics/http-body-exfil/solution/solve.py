#!/usr/bin/env python3
"""Reference solver for http-body-exfil (stdlib only, no scapy).

    python3 solve.py ../capture.pcap

Parse the pcap by hand, pull TCP payloads, keep the HTTP POSTs to
``cdn-metrics.example /collect``, order the bodies by their ``X-Seq`` header,
concatenate, and base64-decode.
"""
import base64
import struct
import sys


def iter_tcp_payloads(path: str):
    data = open(path, "rb").read()
    (magic,) = struct.unpack("<I", data[:4])
    assert magic == 0xA1B2C3D4, "unexpected pcap byte order/magic"
    off = 24  # global header
    while off + 16 <= len(data):
        _ts, _us, incl, _orig = struct.unpack("<IIII", data[off : off + 16])
        off += 16
        frame = data[off : off + incl]
        off += incl
        if len(frame) < 14:
            continue
        eth_type = struct.unpack(">H", frame[12:14])[0]
        if eth_type != 0x0800:
            continue
        ip = frame[14:]
        ihl = (ip[0] & 0x0F) * 4
        if ip[9] != 6:  # not TCP
            continue
        total_len = struct.unpack(">H", ip[2:4])[0]
        tcp = ip[ihl:total_len]
        data_off = (tcp[12] >> 4) * 4
        payload = tcp[data_off:]
        if payload:
            yield payload


def main(path: str) -> None:
    chunks = {}
    for payload in iter_tcp_payloads(path):
        if not payload.startswith(b"POST /collect "):
            continue
        head, _, body = payload.partition(b"\r\n\r\n")
        if b"Host: cdn-metrics.example" not in head:
            continue
        seq = None
        for line in head.split(b"\r\n"):
            if line.lower().startswith(b"x-seq:"):
                seq = int(line.split(b":", 1)[1])
        chunks[seq] = body.decode()

    b64 = "".join(chunks[k] for k in sorted(chunks))
    note = base64.b64decode(b64).decode()
    for line in note.splitlines():
        if line.startswith("exfil-token:"):
            print(line.split(":", 1)[1].strip())
            return
    raise SystemExit("flag not found")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../capture.pcap")
