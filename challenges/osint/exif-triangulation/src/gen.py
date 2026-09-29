"""Generate a bundle of surveillance photos with EXIF GPS metadata.

Four watchers photographed the same target from different spots. Each JPEG
stores the photographer's own position (GPS IFD) AND the coordinates of the
target they observed (GPSDestLatitude/GPSDestLongitude). Three of the four agree
on the same destination; one is a misattribution (decoy). The coordinate the
majority agree on, formatted at 5 decimals, is the flag.

Run:  python3 gen.py   (writes photo_*.jpg to the challenge root)
Requires Pillow + piexif (generation only; the solver is pure stdlib).
"""

import os

import piexif
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The true target the majority triangulate on.
TARGET_LAT, TARGET_LON = 6.13042, 1.22295


def fmt(v: float) -> str:
    return f"{v:.5f}".replace(".", "p")


FLAG = f"NCTF{{triangulated_{fmt(TARGET_LAT)}n_{fmt(TARGET_LON)}e}}"


def to_dms_rationals(dec: float):
    dec = abs(dec)
    deg = int(dec)
    rem = (dec - deg) * 60
    minute = int(rem)
    sec = (rem - minute) * 60
    return ((deg, 1), (minute, 1), (round(sec * 1000), 1000))


def gps_ifd(lat, lon, dlat, dlon, dt):
    return {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: to_dms_rationals(lat),
        piexif.GPSIFD.GPSLongitudeRef: b"E",
        piexif.GPSIFD.GPSLongitude: to_dms_rationals(lon),
        piexif.GPSIFD.GPSDestLatitudeRef: b"N",
        piexif.GPSIFD.GPSDestLatitude: to_dms_rationals(dlat),
        piexif.GPSIFD.GPSDestLongitudeRef: b"E",
        piexif.GPSIFD.GPSDestLongitude: to_dms_rationals(dlon),
        piexif.GPSIFD.GPSDateStamp: dt.encode(),
    }


# filename, watcher_lat, watcher_lon, dest_lat, dest_lon, datetime, color
PHOTOS = [
    (
        "photo_north.jpg",
        6.14100,
        1.22280,
        TARGET_LAT,
        TARGET_LON,
        "2025:08:03 09:14:02",
        (90, 110, 140),
    ),
    (
        "photo_east.jpg",
        6.13050,
        1.23400,
        TARGET_LAT,
        TARGET_LON,
        "2025:08:03 09:15:40",
        (120, 90, 90),
    ),
    (
        "photo_west.jpg",
        6.13010,
        1.21100,
        TARGET_LAT,
        TARGET_LON,
        "2025:08:03 09:16:55",
        (100, 130, 100),
    ),
    # decoy: this watcher pinned the wrong building
    (
        "photo_south.jpg",
        6.11900,
        1.22300,
        6.12550,
        1.21980,
        "2025:08:03 09:20:11",
        (140, 120, 80),
    ),
]


def main() -> None:
    for fname, lat, lon, dlat, dlon, dt, color in PHOTOS:
        img = Image.new("RGB", (96, 64), color)
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: b"CanonSurveil",
                piexif.ImageIFD.Model: b"WatchCam 3",
                piexif.ImageIFD.DateTime: dt.encode(),
            },
            "Exif": {piexif.ExifIFD.DateTimeOriginal: dt.encode()},
            "GPS": gps_ifd(lat, lon, dlat, dlon, dt.split()[0]),
            "1st": {},
            "thumbnail": None,
        }
        img.save(os.path.join(ROOT, fname), exif=piexif.dump(exif_dict))
    print(f"wrote {len(PHOTOS)} photos; target flag = {FLAG}")


if __name__ == "__main__":
    main()
