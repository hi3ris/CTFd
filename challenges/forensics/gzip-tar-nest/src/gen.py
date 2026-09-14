#!/usr/bin/env python3
"""Generate ``parcel.tar.gz`` for the gzip-tar-nest challenge.

A matryoshka of real archives, each format different from its neighbour:

    parcel.tar.gz  (gzip -> tar)
      README.txt          breadcrumb
      level2.zip          (zip)
        level3.tar.gz     (gzip -> tar)
          notes.txt       breadcrumb
          flag.txt        the flag

Every layer is a genuine, tool-openable archive.
"""
import gzip
import io
import tarfile
import time
import zipfile

FLAG = "NCTF{p33l1ng_th3_0ni0n_l4y3r_by_l4y3r}"
MTIME = time.mktime((2024, 5, 1, 12, 0, 0, 0, 0, -1))


def tar_bytes(members: dict) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = MTIME
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def zip_bytes(members: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zi = zipfile.ZipInfo(name, date_time=(2024, 5, 1, 12, 0, 0))
            zf.writestr(zi, data)
    return buf.getvalue()


def gz_bytes(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=int(MTIME)) as gz:
        gz.write(data)
    return buf.getvalue()


def main() -> None:
    level3_tar = tar_bytes(
        {
            "notes.txt": b"You made it to the core. The flag is next to this note.\n",
            "flag.txt": (FLAG + "\n").encode(),
        }
    )
    level3 = gz_bytes(level3_tar)

    level2 = zip_bytes({"level3.tar.gz": level3})

    outer_tar = tar_bytes(
        {
            "README.txt": (
                b"Shipping manifest.\n"
                b"This parcel is packed in layers; each layer is a different "
                b"archive format.\n"
                b"Open level2.zip to continue.\n"
            ),
            "level2.zip": level2,
        }
    )
    parcel = gz_bytes(outer_tar)

    with open("parcel.tar.gz", "wb") as fh:
        fh.write(parcel)
    print(f"wrote parcel.tar.gz ({len(parcel)} bytes), flag={FLAG}")


if __name__ == "__main__":
    main()
