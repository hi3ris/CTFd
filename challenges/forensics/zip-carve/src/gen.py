#!/usr/bin/env python3
"""Generate ``archive.zip`` for the zip-carve challenge.

The archive stores two members, but the central directory has been rewritten so
it only lists the decoy ``notes.txt``. The local file header and data for the
real ``secret.txt`` are still physically present in the stream; standard tools
(``unzip -l``) trust the central directory and never show it. Carving for the
``PK\\x03\\x04`` local-file-header signature recovers the orphaned member.
"""
import struct
import time
import zlib

FLAG = "NCTF{orphan3d_l0cal_h34d3r_c4rv3d}"

NOTES = b"Backup of my project files. Nothing sensitive here, promise.\n"
SECRET = f"internal recovery token -> {FLAG}\n".encode()


def dos_datetime(t: float):
    lt = time.localtime(t)
    dtime = (lt.tm_hour << 11) | (lt.tm_min << 5) | (lt.tm_sec // 2)
    ddate = ((lt.tm_year - 1980) << 9) | (lt.tm_mon << 5) | lt.tm_mday
    return dtime, ddate


def local_header(name: bytes, data: bytes, dtime: int, ddate: int) -> bytes:
    crc = zlib.crc32(data) & 0xFFFFFFFF
    hdr = struct.pack(
        "<IHHHHHIIIHH",
        0x04034B50,
        20,  # version needed
        0,  # flags
        0,  # method: stored
        dtime,
        ddate,
        crc,
        len(data),
        len(data),
        len(name),
        0,
    )
    return hdr + name + data


def central_header(
    name: bytes, data: bytes, offset: int, dtime: int, ddate: int
) -> bytes:
    crc = zlib.crc32(data) & 0xFFFFFFFF
    return (
        struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014B50,
            20,  # version made by
            20,  # version needed
            0,  # flags
            0,  # method
            dtime,
            ddate,
            crc,
            len(data),
            len(data),
            len(name),
            0,  # extra len
            0,  # comment len
            0,  # disk number start
            0,  # internal attrs
            0,  # external attrs
            offset,
        )
        + name
    )


def main() -> None:
    dtime, ddate = dos_datetime(time.mktime((2024, 3, 11, 9, 30, 0, 0, 0, -1)))

    n_notes = b"notes.txt"
    n_secret = b"secret.txt"

    stream = b""
    off_notes = len(stream)
    stream += local_header(n_notes, NOTES, dtime, ddate)
    off_secret = len(stream)
    stream += local_header(n_secret, SECRET, dtime, ddate)

    # Central directory intentionally OMITS secret.txt.
    cd = central_header(n_notes, NOTES, off_notes, dtime, ddate)
    _ = off_secret  # secret.txt exists in the stream but is not indexed

    cd_offset = len(stream)
    eocd = struct.pack(
        "<IHHHHIIH",
        0x06054B50,
        0,
        0,
        1,  # entries this disk (only notes.txt)
        1,  # total entries
        len(cd),
        cd_offset,
        0,
    )

    blob = stream + cd + eocd
    with open("archive.zip", "wb") as fh:
        fh.write(blob)
    print(f"wrote archive.zip ({len(blob)} bytes), flag={FLAG}")


if __name__ == "__main__":
    main()
