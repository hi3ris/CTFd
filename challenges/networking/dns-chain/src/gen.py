#!/usr/bin/env python3
"""Build a raw DNS response message (RFC 1035 wire format, with name compression).

The answer section holds a CNAME chain starting at the question name, plus a TXT
record for every name in the chain. Following the chain from the question name
and concatenating each hop's TXT string yields the flag. Owner names reuse the
common ".flag.nctf" suffix via compression pointers (0xC0), so the player must
implement pointer-following, not just label walking.

Output: message.bin (raw bytes) and message.hex (same bytes, hex, for viewing).
"""

import os
import random
import struct

FLAG = b"NCTF{dns_wire_format_cname_chain_txt_with_compression}"

TYPE_A = 1
TYPE_CNAME = 5
TYPE_TXT = 16
CLASS_IN = 1


def main():
    rng = random.Random(0xD5C0DE)

    # split flag into chunks -> one hop per chunk
    chunks = []
    i = 0
    while i < len(FLAG):
        n = rng.randint(4, 7)
        chunks.append(FLAG[i : i + n])
        i += n
    nhops = len(chunks)

    suffix = [b"flag", b"nctf"]
    names = [[b"h%02d" % k] + suffix for k in range(nhops)]
    qname = names[0]

    buf = bytearray()
    name_offsets = {}

    def write_name(labels):
        labels = list(labels)
        while labels:
            key = tuple(labels)
            if key in name_offsets:
                buf.extend(struct.pack(">H", 0xC000 | name_offsets[key]))
                return
            name_offsets[key] = len(buf)
            buf.append(len(labels[0]))
            buf.extend(labels[0])
            labels = labels[1:]
        buf.append(0)

    # header: id, flags(response), qd=1, an=count, ns=0, ar=0
    answers = []
    for k in range(nhops):
        if k + 1 < nhops:
            answers.append(("cname", names[k], names[k + 1]))
        answers.append(("txt", names[k], chunks[k]))
    rng.shuffle(answers)

    buf.extend(struct.pack(">HHHHHH", 0x1337, 0x8180, 1, len(answers), 0, 0))

    # question
    write_name(qname)
    buf.extend(struct.pack(">HH", TYPE_A, CLASS_IN))

    # answers
    for kind, owner, data in answers:
        write_name(owner)
        if kind == "cname":
            buf.extend(struct.pack(">HHI", TYPE_CNAME, CLASS_IN, 300))
            rdlen_pos = len(buf)
            buf.extend(b"\x00\x00")  # placeholder rdlength
            start = len(buf)
            write_name(data)
            rdlen = len(buf) - start
            struct.pack_into(">H", buf, rdlen_pos, rdlen)
        else:
            buf.extend(struct.pack(">HHI", TYPE_TXT, CLASS_IN, 300))
            # TXT rdata: one character-string (len byte + bytes)
            rdata = bytes([len(data)]) + data
            buf.extend(struct.pack(">H", len(rdata)))
            buf.extend(rdata)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "message.bin"), "wb") as f:
        f.write(buf)
    with open(os.path.join(here, "..", "message.hex"), "w") as f:
        h = buf.hex()
        f.write("\n".join(h[j : j + 64] for j in range(0, len(h), 64)))
        f.write("\n")
    print(
        "wrote message.bin bytes=%d hops=%d answers=%d"
        % (len(buf), nhops, len(answers))
    )


if __name__ == "__main__":
    main()
