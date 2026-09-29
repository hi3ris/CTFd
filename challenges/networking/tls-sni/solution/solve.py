#!/usr/bin/env python3
"""Parse the TLS ClientHello, pull the SNI host, decode the flag from its labels."""

import os
import struct


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    rec = open(os.path.join(here, "..", "clienthello.bin"), "rb").read()

    assert rec[0] == 0x16, "not a handshake record"
    rec_len = struct.unpack(">H", rec[3:5])[0]
    hs = rec[5 : 5 + rec_len]

    assert hs[0] == 0x01, "not a ClientHello"
    off = 4  # skip handshake type + 3-byte length
    off += 2  # client_version
    off += 32  # random
    sid_len = hs[off]
    off += 1 + sid_len
    cs_len = struct.unpack(">H", hs[off : off + 2])[0]
    off += 2 + cs_len
    comp_len = hs[off]
    off += 1 + comp_len

    ext_total = struct.unpack(">H", hs[off : off + 2])[0]
    off += 2
    end = off + ext_total

    host = None
    while off < end:
        etype, elen = struct.unpack(">HH", hs[off : off + 4])
        off += 4
        body = hs[off : off + elen]
        off += elen
        if etype == 0x0000:  # server_name
            # list_len(2), name_type(1), name_len(2), name
            name_type = body[2]
            assert name_type == 0
            nlen = struct.unpack(">H", body[3:5])[0]
            host = body[5 : 5 + nlen].decode()
            break

    assert host is not None, "no SNI"
    labels = host.split(".")
    assert labels[-2:] == ["v", "nctf"], labels
    hexpart = "".join(labels[:-2])
    print(bytes.fromhex(hexpart).decode())


if __name__ == "__main__":
    main()
