#!/usr/bin/env python3
"""Reference solver for icmp-beacon (stdlib only, no scapy).

    python3 solve.py ../icmp.pcap

Parse the pcap, keep ICMP echo REQUESTS (type 8) to the covert host, sort by the
ICMP sequence number, and read the one flag byte at payload offset 8 from each.
"""
import struct
import sys

C2 = "192.168.50.200"
FLAG_OFFSET = 8


def main(path: str) -> None:
    data = open(path, "rb").read()
    assert struct.unpack("<I", data[:4])[0] == 0xA1B2C3D4
    off = 24
    chars = {}  # seq -> char
    while off + 16 <= len(data):
        _ts, _us, incl, _orig = struct.unpack("<IIII", data[off : off + 16])
        off += 16
        frame = data[off : off + incl]
        off += incl
        if len(frame) < 14 or struct.unpack(">H", frame[12:14])[0] != 0x0800:
            continue
        ip = frame[14:]
        ihl = (ip[0] & 0x0F) * 4
        if ip[9] != 1:  # not ICMP
            continue
        dst = ".".join(str(b) for b in ip[16:20])
        icmp = ip[ihl:]
        icmp_type = icmp[0]
        if icmp_type != 8 or dst != C2:  # echo request to the covert host only
            continue
        seq = struct.unpack(">H", icmp[6:8])[0]
        payload = icmp[8:]
        chars[seq] = chr(payload[FLAG_OFFSET])

    flag = "".join(chars[k] for k in sorted(chars))
    print(flag)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../icmp.pcap")
