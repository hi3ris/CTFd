#!/usr/bin/env python3
"""Build a raw TLS ClientHello record; the flag hides in the SNI hostname.

No crypto is involved -- only TLS record + handshake structure parsing:

    record: type(1)=0x16 | version(2) | length(2)
    handshake: type(1)=0x01 | length(3)
    client_version(2) | random(32) | session_id(len+data)
    cipher_suites(len2+data) | compression(len1+data)
    extensions(len2 + [type(2) len(2) data]...)

The server_name in the SNI extension is
"<hex0>.<hex1>...<hexN>.v.nctf"; the hex labels (before the fixed "v.nctf"
suffix) concatenate and hex-decode to the flag. Decoy ASCII is planted in the
client random and an ALPN entry to punish grep-only solvers.
"""

import os
import struct

FLAG = b"NCTF{tls_client_hello_sni_extension_parsed_no_crypto}"


def build_sni_host():
    # split flag into hex-label chunks, then append fixed suffix
    labels = []
    i = 0
    step = 5
    while i < len(FLAG):
        labels.append(FLAG[i : i + step].hex())
        i += step
    labels += ["v", "nctf"]
    return ".".join(labels).encode()


def ext(etype, data):
    return struct.pack(">HH", etype, len(data)) + data


def main():
    host = build_sni_host()

    # SNI extension (type 0)
    server_name = (
        bytes([0]) + struct.pack(">H", len(host)) + host
    )  # name_type=0 host_name
    sni_list = struct.pack(">H", len(server_name)) + server_name
    sni_ext = ext(0x0000, sni_list)

    # ALPN (type 16) with a decoy string to trap grep
    protos = [b"h2", b"NOT_THE_FLAG", b"http/1.1"]
    alpn_body = b"".join(bytes([len(p)]) + p for p in protos)
    alpn = struct.pack(">H", len(alpn_body)) + alpn_body
    alpn_ext = ext(0x0010, alpn)

    # supported_versions (type 43): TLS1.3, TLS1.2
    sv_body = bytes([4]) + struct.pack(">HH", 0x0304, 0x0303)
    sv_ext = ext(0x002B, sv_body)

    extensions = sni_ext + alpn_ext + sv_ext
    ext_block = struct.pack(">H", len(extensions)) + extensions

    client_version = struct.pack(">H", 0x0303)
    # 32-byte random with an embedded decoy ASCII string
    random_bytes = b"decoyNCTF{not_here}...paddingpad"[:32]
    assert len(random_bytes) == 32
    session_id = bytes([0])  # empty
    cipher_suites = struct.pack(">H", 4) + struct.pack(">HH", 0x1301, 0xC02F)
    compression = bytes([1, 0])  # 1 method: null

    hs_body = (
        client_version
        + random_bytes
        + session_id
        + cipher_suites
        + compression
        + ext_block
    )
    handshake = (
        bytes([0x01]) + struct.pack(">I", len(hs_body))[1:] + hs_body
    )  # 3-byte len
    record = (
        bytes([0x16])
        + struct.pack(">H", 0x0301)
        + struct.pack(">H", len(handshake))
        + handshake
    )

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "clienthello.bin"), "wb") as f:
        f.write(record)
    with open(os.path.join(here, "..", "clienthello.hex"), "w") as f:
        h = record.hex()
        f.write("\n".join(h[j : j + 64] for j in range(0, len(h), 64)))
        f.write("\n")
    print("wrote clienthello.bin bytes=%d sni=%s" % (len(record), host.decode()))


if __name__ == "__main__":
    main()
