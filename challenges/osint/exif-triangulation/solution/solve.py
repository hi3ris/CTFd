#!/usr/bin/env python3
"""Pure-stdlib EXIF GPS reader. Extract each photo's observed-target coordinate
(GPSDestLatitude/GPSDestLongitude), majority-vote the agreed target, and format
it into the flag."""

import glob
import os
import struct
from collections import Counter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

GPS_IFD_TAG = 0x8825
DEST_LAT, DEST_LAT_REF = 0x14, 0x13
DEST_LON, DEST_LON_REF = 0x16, 0x15


def find_tiff(data: bytes) -> int:
    i = 2  # skip SOI
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        seg_len = struct.unpack(">H", data[i + 2 : i + 4])[0]
        if marker == 0xE1 and data[i + 4 : i + 10] == b"Exif\x00\x00":
            return i + 10
        i += 2 + seg_len
    raise ValueError("no Exif APP1")


def parse_ifd(data: bytes, tiff: int, ifd_off: int, endian: str):
    count = struct.unpack(endian + "H", data[tiff + ifd_off : tiff + ifd_off + 2])[0]
    entries = {}
    base = tiff + ifd_off + 2
    for n in range(count):
        e = base + n * 12
        tag, typ, cnt = struct.unpack(endian + "HHI", data[e : e + 8])
        entries[tag] = (typ, cnt, data[e + 8 : e + 12])
    return entries


def read_rationals(data, tiff, endian, valoff, cnt):
    off = tiff + struct.unpack(endian + "I", valoff)[0]
    out = []
    for k in range(cnt):
        num, den = struct.unpack(endian + "II", data[off + k * 8 : off + k * 8 + 8])
        out.append(num / den)
    return out


def read_ascii(valoff):
    return valoff.split(b"\x00")[0].decode()


def dest_coord(path: str):
    data = open(path, "rb").read()
    tiff = find_tiff(data)
    endian = "<" if data[tiff : tiff + 2] == b"II" else ">"
    ifd0_off = struct.unpack(endian + "I", data[tiff + 4 : tiff + 8])[0]
    ifd0 = parse_ifd(data, tiff, ifd0_off, endian)
    gps_off = struct.unpack(endian + "I", ifd0[GPS_IFD_TAG][2])[0]
    gps = parse_ifd(data, tiff, gps_off, endian)

    lat = read_rationals(data, tiff, endian, gps[DEST_LAT][2], gps[DEST_LAT][1])
    lon = read_rationals(data, tiff, endian, gps[DEST_LON][2], gps[DEST_LON][1])
    latref = read_ascii(gps[DEST_LAT_REF][2])
    lonref = read_ascii(gps[DEST_LON_REF][2])

    dlat = lat[0] + lat[1] / 60 + lat[2] / 3600
    dlon = lon[0] + lon[1] / 60 + lon[2] / 3600
    if latref == "S":
        dlat = -dlat
    if lonref == "W":
        dlon = -dlon
    return round(dlat, 5), round(dlon, 5)


def main() -> None:
    coords = [
        dest_coord(p) for p in sorted(glob.glob(os.path.join(ROOT, "photo_*.jpg")))
    ]
    (lat, lon), _ = Counter(coords).most_common(1)[0]
    lat_s = f"{lat:.5f}".replace(".", "p")
    lon_s = f"{lon:.5f}".replace(".", "p")
    print(f"NCTF{{triangulated_{lat_s}n_{lon_s}e}}")


if __name__ == "__main__":
    main()
