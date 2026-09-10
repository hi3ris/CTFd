#!/usr/bin/env python3
"""
gatepkt.py -- reference codec for the invented QGP1 badge container.

This is the ONLY format the SENTRY-6 gate accepts on /submit. It is NOT PNG,
NPY, DER, protobuf or any standard container -- it is a small invented TLV with
three deliberately non-standard conventions. The handout ships sample .gatepkt
files plus a partial spec; players are expected to infer the exact rules from
that evidence and then produce a well-formed packet carrying their adversarial
badge.

WIRE FORMAT (all multi-byte fields little-endian)
-------------------------------------------------
Header, 12 bytes:
    [0:4]   magic       = b"QGP\\x01"
    [4]     nrows       (uint8)  number of pixel rows
    [5]     ncols       (uint8)  number of pixel columns
    [6]     flags       (uint8)  bit0 = rows are stored BOTTOM-TO-TOP
    [7]     reserved    (uint8)  = 0
    [8:10]  hdr_sum     (uint16) checksum = (sum of header bytes [0:8]) & 0xFFFF
                                 --> computed over the HEADER ONLY, never the body
    [10:12] rec_count   (uint16) number of pixel RECORDS that follow
                                 --> this counts RECORDS (rows), NOT bytes,
                                     and MUST equal nrows

Body: `rec_count` records, each:
    [0]     rlen        (uint8)  = ncols
    [1:1+rlen]          rlen raw pixel bytes (0..255) for that row

Quirks that trip a naive "just dump the pixels" encoder:
    (1) the length field counts records, not bytes;
    (2) the checksum covers the header only;
    (3) when flags bit0 is set the FIRST record in the file is the BOTTOM
        image row, so the pixel plane is stored upside down.

`encode` here always emits flags bit0 = 1 (bottom-to-top), matching every
shipped sample. `decode` is strict: any field that disagrees with the spec
above raises GatePktError, so a malformed submission is rejected by the gate
rather than silently mis-scored.
"""

MAGIC = b"QGP\x01"


class GatePktError(ValueError):
    pass


def _u16(b, off):
    return b[off] | (b[off + 1] << 8)


def encode(img, bottom_to_top=True):
    """img: 2D list/array of ints, shape (nrows, ncols), values 0..255."""
    rows = [list(int(v) & 0xFF for v in r) for r in img]
    nrows = len(rows)
    ncols = len(rows[0]) if rows else 0
    if any(len(r) != ncols for r in rows):
        raise GatePktError("ragged image")
    if nrows > 255 or ncols > 255:
        raise GatePktError("dims must fit in a byte")
    flags = 0x01 if bottom_to_top else 0x00
    header = bytearray(12)
    header[0:4] = MAGIC
    header[4] = nrows
    header[5] = ncols
    header[6] = flags
    header[7] = 0
    hdr_sum = sum(header[0:8]) & 0xFFFF
    header[8] = hdr_sum & 0xFF
    header[9] = (hdr_sum >> 8) & 0xFF
    header[10] = nrows & 0xFF
    header[11] = (nrows >> 8) & 0xFF

    stored = rows[::-1] if bottom_to_top else rows
    body = bytearray()
    for r in stored:
        body.append(ncols)
        body.extend(r)
    return bytes(header) + bytes(body)


def decode(blob):
    """Return a list-of-lists uint8 image, or raise GatePktError."""
    if len(blob) < 12:
        raise GatePktError("short header")
    if bytes(blob[0:4]) != MAGIC:
        raise GatePktError("bad magic")
    nrows = blob[4]
    ncols = blob[5]
    flags = blob[6]
    if blob[7] != 0:
        raise GatePktError("reserved must be zero")
    hdr_sum = _u16(blob, 8)
    if hdr_sum != (sum(blob[0:8]) & 0xFFFF):
        raise GatePktError("header checksum mismatch")
    rec_count = _u16(blob, 10)
    if rec_count != nrows:
        raise GatePktError("rec_count must count records (== nrows)")

    off = 12
    rows = []
    for _ in range(rec_count):
        if off >= len(blob):
            raise GatePktError("truncated body")
        rlen = blob[off]
        off += 1
        if rlen != ncols:
            raise GatePktError("record length must equal ncols")
        if off + rlen > len(blob):
            raise GatePktError("truncated record")
        rows.append(list(blob[off:off + rlen]))
        off += rlen
    if off != len(blob):
        raise GatePktError("trailing bytes after body")

    if flags & 0x01:
        rows = rows[::-1]
    return rows
