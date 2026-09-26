#!/usr/bin/env python3
"""Generate ``icmp.pcap`` for the icmp-beacon challenge.

A libpcap capture (linktype EN10MB) written with a tiny hand-rolled writer.
Two hosts are pinged. Traffic to ``192.168.50.10`` is ordinary ping (the classic
``\\x08\\x09...`` payload pattern). Traffic to ``192.168.50.200`` is a covert
channel: each ICMP echo request hides exactly one flag byte at payload offset 8,
and the ICMP sequence number gives its position. Reassemble by sequence number
to recover the flag.
"""
import random
import struct

FLAG = "NCTF{1cmp_p4yl04d_c0v3rt_ch4nn3l}"

random.seed(4242)

FLAG_OFFSET = 8  # byte index inside the ICMP payload that carries a flag char


def checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    s = sum(struct.unpack(f">{len(data)//2}H", data))
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return (~s) & 0xFFFF


def ip2b(ip: str) -> bytes:
    return bytes(int(o) for o in ip.split("."))


def icmp_echo(ident: int, seq: int, payload: bytes) -> bytes:
    hdr = struct.pack(">BBHHH", 8, 0, 0, ident, seq)  # type 8 echo request
    csum = checksum(hdr + payload)
    return struct.pack(">BBHHH", 8, 0, csum, ident, seq) + payload


def ipv4(src: str, dst: str, proto: int, payload: bytes) -> bytes:
    total = 20 + len(payload)
    hdr = (
        struct.pack(
            ">BBHHHBBH",
            0x45,
            0,
            total,
            random.randint(0, 0xFFFF),
            0,
            64,
            proto,
            0,
        )
        + ip2b(src)
        + ip2b(dst)
    )
    csum = checksum(hdr)
    hdr = hdr[:10] + struct.pack(">H", csum) + hdr[12:]
    return hdr + payload


def frame(src: str, dst: str, icmp: bytes) -> bytes:
    eth = b"\x52\x54\x00\x11\x22\x33" + b"\x52\x54\x00\xaa\xbb\xcc" + b"\x08\x00"
    return eth + ipv4(src, dst, 1, icmp)


class PcapWriter:
    def __init__(self, path: str):
        self.fh = open(path, "wb")
        self.fh.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        self.ts = 1_711_000_000

    def write(self, fr: bytes):
        self.ts += random.randint(1, 2)
        self.fh.write(
            struct.pack("<IIII", self.ts, random.randint(0, 999999), len(fr), len(fr))
        )
        self.fh.write(fr)

    def close(self):
        self.fh.close()


def std_payload() -> bytes:
    # Linux ping-style payload: 8-byte timestamp region + 0x08..0x37 pattern.
    return bytes(range(0x08, 0x08 + 48))


def main() -> None:
    host = "192.168.5.66"
    benign = "192.168.50.10"
    c2 = "192.168.50.200"

    frames = []

    # covert channel: one flag byte per packet at FLAG_OFFSET, ordered by seq
    ident = 0x4C3A
    for i, ch in enumerate(FLAG):
        payload = bytearray(std_payload())
        payload[FLAG_OFFSET] = ord(ch)
        req = icmp_echo(ident, i, bytes(payload))
        frames.append((host, c2, req))

    # benign pings to another host (standard payload, unrelated ident/seq)
    for i in range(20):
        req = icmp_echo(0x1001, i, std_payload())
        frames.append((host, benign, req))

    # a few echo REPLIES from the c2 host (noise; type 0, ignore in solve)
    for i in range(5):
        payload = std_payload()
        hdr = struct.pack(">BBHHH", 0, 0, 0, ident, i)
        csum = checksum(hdr + payload)
        reply = struct.pack(">BBHHH", 0, 0, csum, ident, i) + payload
        frames.append((c2, host, reply))

    random.shuffle(frames)

    w = PcapWriter("icmp.pcap")
    for src, dst, icmp in frames:
        w.write(frame(src, dst, icmp))
    w.close()

    import os

    print(
        f"wrote icmp.pcap ({os.path.getsize('icmp.pcap')} bytes), "
        f"{len(FLAG)} covert packets, flag={FLAG}"
    )


if __name__ == "__main__":
    main()
