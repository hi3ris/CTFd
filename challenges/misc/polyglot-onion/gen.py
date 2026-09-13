#!/usr/bin/env python3
"""
Deterministic generator for the `polyglot-onion` challenge handout.

Builds a single file `keepsake.png` that is a nested polyglot / onion of
ordinary file formats. Each layer is a *genuine* file of its type (so `file`
identifies it) but hides the next layer; none of the layers announces the
encoding of the one below it -- the player deduces each step from magic bytes
and structure.

Onion, from the OUTSIDE in:

  L0  keepsake.png        valid PNG image (renders); ZIP archive appended
                          after the IEND chunk
  L1  <zip entry>         the single stored ZIP entry is Ascii85 text
                          (Adobe framing  <~ ... ~>)
  L2  <ascii85 decoded>   a gzip stream          (magic 1f 8b)
  L3  <gunzipped>         a bzip2 stream         (magic 42 5a 68 -> "BZh")
  L4  <bunzip2'd>         a POSIX tar archive    ("ustar" at offset 257)
  L5  flag.txt            the flag

The flag string only ever exists at L5; everything outward is a
compression/encoding of it, so it never appears verbatim in the handout.

Reproducible: no wall-clock input. All timestamps are pinned to 0 and the
image content is generated from a fixed formula, so re-running produces a
byte-identical `keepsake.png`.
"""

import base64
import bz2
import gzip
import io
import struct
import tarfile
import zipfile
import zlib
import os

FLAG = b"NCTF{magic_byt3s_unm4sk_3v3ry_l4y3r}\n"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "keepsake.png")


# ---------------------------------------------------------------------------
# L5 -> L4 : put the flag in a tar archive (single member flag.txt)
# ---------------------------------------------------------------------------
def build_tar(payload: bytes) -> bytes:
    buf = io.BytesIO()
    # gzip=False here; plain tar. Deterministic: fixed mtime/uid/gid/uname.
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tf:
        info = tarfile.TarInfo(name="flag.txt")
        info.size = len(payload)
        info.mtime = 0
        info.mode = 0o644
        info.uid = 0
        info.gid = 0
        info.uname = ""
        info.gname = ""
        tf.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# L4 -> L3 : bzip2 compress
# ---------------------------------------------------------------------------
def build_bzip2(data: bytes) -> bytes:
    return bz2.compress(data, 9)


# ---------------------------------------------------------------------------
# L3 -> L2 : gzip compress (mtime pinned to 0 for reproducibility)
# ---------------------------------------------------------------------------
def build_gzip(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0) as gz:
        gz.write(data)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# L2 -> L1 : Ascii85 encode (Adobe framing so the <~ ... ~> gives it away)
# ---------------------------------------------------------------------------
def build_ascii85(data: bytes) -> bytes:
    return base64.a85encode(data, adobe=True, wrapcol=76)


# ---------------------------------------------------------------------------
# L1 -> (zip) : store the Ascii85 text as a single ZIP entry.
# Deterministic: ZIP_STORED, fixed date_time.
# ---------------------------------------------------------------------------
def build_zip(a85: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        zi = zipfile.ZipInfo(filename="scrap.txt", date_time=(1980, 1, 1, 0, 0, 0))
        zi.external_attr = 0o644 << 16
        zf.writestr(zi, a85)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# L0 : a genuine, renderable PNG. Built by hand so it is deterministic and a
# real image (a smooth diagonal gradient), then the ZIP is appended after IEND.
# ---------------------------------------------------------------------------
def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def build_png(width: int = 96, height: int = 96) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    # raw scanlines: filter byte 0 + RGB pixels from a fixed formula
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type: None
        for x in range(width):
            r = (x * 255) // (width - 1)
            g = (y * 255) // (height - 1)
            b = ((x + y) * 255) // (width + height - 2)
            raw += bytes((r, g, b))
    idat = zlib.compress(bytes(raw), 9)
    return (
        sig
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def main() -> None:
    tar_bytes = build_tar(FLAG)          # L4
    bz_bytes = build_bzip2(tar_bytes)    # L3
    gz_bytes = build_gzip(bz_bytes)      # L2
    a85_bytes = build_ascii85(gz_bytes)  # L1
    zip_bytes = build_zip(a85_bytes)     # zip container
    png_bytes = build_png()              # L0 valid image

    handout = png_bytes + zip_bytes      # PNG + appended ZIP polyglot

    with open(OUT, "wb") as f:
        f.write(handout)

    # sanity: the flag must NOT appear verbatim anywhere in the handout
    assert FLAG.strip() not in handout, "flag leaked into handout!"
    print(f"wrote {OUT} ({len(handout)} bytes)")
    print(f"  L0 png bytes : {len(png_bytes)}")
    print(f"  zip appended : {len(zip_bytes)}")


if __name__ == "__main__":
    main()
