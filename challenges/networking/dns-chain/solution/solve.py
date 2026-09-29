#!/usr/bin/env python3
"""Parse the raw DNS message, follow the CNAME chain, concatenate TXT strings."""

import os
import struct


def read_name(msg, off):
    labels = []
    jumped = False
    end = off
    while True:
        length = msg[off]
        if length == 0:
            off += 1
            if not jumped:
                end = off
            break
        if length & 0xC0 == 0xC0:
            ptr = ((length & 0x3F) << 8) | msg[off + 1]
            if not jumped:
                end = off + 2
            off = ptr
            jumped = True
            continue
        labels.append(msg[off + 1 : off + 1 + length])
        off += 1 + length
    return labels, end


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    msg = open(os.path.join(here, "..", "message.bin"), "rb").read()

    _id, _flags, qd, an, _ns, _ar = struct.unpack(">HHHHHH", msg[:12])
    off = 12
    qname, off = read_name(msg, off)
    off += 4  # qtype + qclass

    cname = {}  # owner-name-tuple -> target-name-tuple
    txt = {}  # owner-name-tuple -> string bytes
    for _ in range(an):
        owner, off = read_name(msg, off)
        rtype, _cls, _ttl, rdlen = struct.unpack(">HHIH", msg[off : off + 10])
        off += 10
        rdata_start = off
        if rtype == 5:  # CNAME
            target, _ = read_name(msg, off)
            cname[tuple(owner)] = tuple(target)
        elif rtype == 16:  # TXT
            slen = msg[off]
            txt[tuple(owner)] = msg[off + 1 : off + 1 + slen]
        off = rdata_start + rdlen

    # walk the chain from the question name
    cur = tuple(qname)
    out = b""
    seen = set()
    while cur is not None and cur not in seen:
        seen.add(cur)
        out += txt.get(cur, b"")
        cur = cname.get(cur)
    print(out.decode())


if __name__ == "__main__":
    main()
