"""Generate a phone "device backup" made of SQLite databases.

Artifacts (under backup/):
  * messages.sqlite  sms table + an encrypted self-note (notes table)
  * location.sqlite  GPS fix history (ts epoch, lat, lon, accuracy)
  * celltower.sqlite  serving-cell log (corroborating flavour)
  * photos.sqlite    geotagged photos (one is a decoy in another town)

Pivot: an SMS confirms a rendezvous at a precise UTC datetime. Look up the GPS
fix at that exact timestamp; its coordinates (canonical "lat,lon" at 6 dp) key
the sha256-CTR keystream that decrypts the self-note, which holds the flag.

Run:  python3 gen.py
"""

import hashlib
import os
import sqlite3
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BACKUP = os.path.join(ROOT, "backup")

FLAG = "NCTF{device_backup_geo_rendezvous_pinned}"

RDV_ISO = "2025-07-12 14:32:00"
RDV_TS = int(
    datetime.strptime(RDV_ISO, "%Y-%m-%d %H:%M:%S")
    .replace(tzinfo=timezone.utc)
    .timestamp()
)

# rendezvous coordinates (Grand Marche, Lome) — the fix stored at RDV_TS
RDV_LAT, RDV_LON = 6.130419, 1.222954


def keystream(key: str, n: int) -> bytes:
    out = bytearray()
    c = 0
    while len(out) < n:
        out += hashlib.sha256(key.encode() + c.to_bytes(4, "big")).digest()
        c += 1
    return bytes(out[:n])


def geo_key(lat: float, lon: float) -> str:
    return f"{lat:.6f},{lon:.6f}"


def build_messages() -> None:
    path = os.path.join(BACKUP, "messages.sqlite")
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.executescript(
        "CREATE TABLE sms(ts INTEGER, sender TEXT, body TEXT);"
        "CREATE TABLE notes(id INTEGER PRIMARY KEY, cipher BLOB);"
    )
    sms = [
        (RDV_TS - 86400, "+22890114477", "salut, on se voit demain?"),
        (
            RDV_TS - 3600,
            "+22890114477",
            "RDV confirme le 2025-07-12 14:32:00 UTC. viens seul.",
        ),
        (RDV_TS - 3600, "+22899001122", "promo credit: rechargez 1000 F"),
        (RDV_TS + 7200, "+22890114477", "c'etait bien. efface la note."),
    ]
    con.executemany("INSERT INTO sms VALUES (?,?,?)", sms)

    note = f"note perso: point de chute confirme. token={FLAG}".encode()
    key = geo_key(RDV_LAT, RDV_LON)
    cipher = bytes(a ^ b for a, b in zip(note, keystream(key, len(note))))
    con.execute("INSERT INTO notes(cipher) VALUES (?)", (cipher,))
    con.commit()
    con.close()


def build_location() -> None:
    path = os.path.join(BACKUP, "location.sqlite")
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE locations(ts INTEGER, lat REAL, lon REAL, accuracy INTEGER, source TEXT)"
    )
    rows = [
        (RDV_TS - 7200, 6.172500, 1.231100, 20, "gps"),  # home
        (RDV_TS - 3000, 6.150000, 1.225000, 35, "wifi"),  # en route
        (RDV_TS, RDV_LAT, RDV_LON, 8, "gps"),  # <-- the rendezvous fix
        (RDV_TS + 1800, 6.131000, 1.223500, 40, "wifi"),  # nearby, after
        (RDV_TS + 5400, 6.172400, 1.231000, 18, "gps"),  # back home
    ]
    con.executemany("INSERT INTO locations VALUES (?,?,?,?,?)", rows)
    con.commit()
    con.close()


def build_celltower() -> None:
    path = os.path.join(BACKUP, "celltower.sqlite")
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE cell(ts INTEGER, mcc INTEGER, mnc INTEGER, lac INTEGER, cellid INTEGER, rssi INTEGER)"
    )
    rows = [
        (RDV_TS - 7200, 615, 1, 4101, 22011, -71),
        (RDV_TS, 615, 1, 4107, 30455, -63),
        (RDV_TS + 5400, 615, 1, 4101, 22011, -69),
    ]
    con.executemany("INSERT INTO cell VALUES (?,?,?,?,?,?)", rows)
    con.commit()
    con.close()


def build_photos() -> None:
    path = os.path.join(BACKUP, "photos.sqlite")
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE photo(filename TEXT, ts INTEGER, lat REAL, lon REAL)")
    rows = [
        ("IMG_012.jpg", RDV_TS - 200000, 9.551000, 1.186000),  # Kara, decoy
        ("IMG_020.jpg", RDV_TS + 30, 6.130800, 1.223100),
    ]
    con.executemany("INSERT INTO photo VALUES (?,?,?,?)", rows)
    con.commit()
    con.close()


def main() -> None:
    os.makedirs(BACKUP, exist_ok=True)
    build_messages()
    build_location()
    build_celltower()
    build_photos()
    print(
        "wrote backup/messages.sqlite, location.sqlite, celltower.sqlite, photos.sqlite"
    )


if __name__ == "__main__":
    main()
