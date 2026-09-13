#!/usr/bin/env python3
"""
Reference solver for `polyglot-onion`.

Peels the handout layer by layer. Nothing about the layout is hard-coded from
the challenge: at every step the solver INSPECTS the bytes it currently holds,
figures out what kind of file it is from magic bytes / structure, and applies
the matching transform. It stops when it reaches printable text carrying the
flag.

Usage:
    python3 solve.py [path-to-keepsake.png]

Defaults to ../keepsake.png relative to this script.
"""

import base64
import bz2
import gzip
import io
import os
import re
import sys
import tarfile
import zipfile

FLAG_RE = re.compile(rb"NCTF\{[^}]+\}")


def find_flag(data: bytes):
    m = FLAG_RE.search(data)
    return m.group(0) if m else None


# --- layer detectors / peelers -------------------------------------------

def peel_png_trailer(data: bytes):
    """A PNG whose bytes continue past the IEND chunk hide something after it.
    Return everything following the IEND chunk (its 4-byte CRC included)."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    idx = data.find(b"IEND")
    if idx == -1:
        return None
    end = idx + 4 + 4  # "IEND" + 4-byte CRC
    trailer = data[end:]
    return trailer if trailer else None


def peel_zip(data: bytes):
    """A ZIP (or a blob with an appended ZIP): read the single member.
    zipfile tolerates leading junk, but here we already carved to the PK data."""
    if b"PK\x03\x04" not in data[:4] and not data.startswith(b"PK"):
        # allow appended-zip case: locate the first local file header
        pos = data.find(b"PK\x03\x04")
        if pos == -1:
            return None
        data = data[pos:]
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            if not names:
                return None
            return zf.read(names[0])
    except zipfile.BadZipFile:
        return None


def peel_ascii85(data: bytes):
    """Adobe-framed Ascii85 text: <~ ... ~>."""
    s = data.strip()
    if not (s.startswith(b"<~") and s.rstrip().endswith(b"~>")):
        return None
    try:
        return base64.a85decode(s, adobe=True)
    except Exception:
        return None


def peel_gzip(data: bytes):
    """gzip stream: magic 1f 8b."""
    if not data.startswith(b"\x1f\x8b"):
        return None
    try:
        return gzip.decompress(data)
    except Exception:
        return None


def peel_bzip2(data: bytes):
    """bzip2 stream: magic 'BZh'."""
    if not data.startswith(b"BZh"):
        return None
    try:
        return bz2.decompress(data)
    except Exception:
        return None


def peel_tar(data: bytes):
    """POSIX tar: 'ustar' at offset 257. Return the first member's bytes."""
    if len(data) < 265 or data[257:262] != b"ustar":
        return None
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as tf:
            members = [m for m in tf.getmembers() if m.isfile()]
            if not members:
                return None
            f = tf.extractfile(members[0])
            return f.read() if f else None
    except tarfile.TarError:
        return None


PEELERS = [
    ("png-trailer", peel_png_trailer),
    ("zip", peel_zip),
    ("ascii85", peel_ascii85),
    ("gzip", peel_gzip),
    ("bzip2", peel_bzip2),
    ("tar", peel_tar),
]


def solve(data: bytes) -> bytes:
    layer = 0
    while True:
        flag = find_flag(data)
        if flag:
            print(f"[layer {layer}] flag found")
            return flag
        for name, fn in PEELERS:
            out = fn(data)
            if out is not None and out != data:
                print(f"[layer {layer}] detected {name:<12} -> {len(out)} bytes")
                data = out
                layer += 1
                break
        else:
            raise SystemExit(
                f"[layer {layer}] no known layer matched; stuck on "
                f"{data[:16]!r}"
            )


def main() -> None:
    default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "keepsake.png")
    path = sys.argv[1] if len(sys.argv) > 1 else default
    with open(path, "rb") as f:
        data = f.read()
    flag = solve(data)
    print(flag.decode())


if __name__ == "__main__":
    main()
