#!/usr/bin/env python3
"""
Solver for usb-keystrokes.

Reads a Linux usbmon (LINKTYPE_USB_LINUX_MMAPPED, DLT 220) pcap, isolates the
keyboard's HID boot reports and decodes them into the typed passphrase.

The interesting parts of the solve:
  * usbmon URBs carry a 64-byte header; the HID report is the captured data
    that follows it. We parse the header rather than blindly slicing bytes.
  * Both SUBMIT and COMPLETE events appear; only COMPLETE interrupt-IN packets
    carry the 8-byte report, so we key on len_cap == 8.
  * Two devices are on the bus. The mouse (device 5, 4-byte reports) is a
    decoy - filtering to the keyboard's device address removes it cleanly.
  * The boot keyboard report is [modifier, reserved, k1..k6]; a left/right
    shift bit in the modifier byte selects the shifted character.

Usage:  python3 solve.py [capture.pcap]
"""
import struct
import sys

HID = {
    0x04: ("a", "A"), 0x05: ("b", "B"), 0x06: ("c", "C"), 0x07: ("d", "D"),
    0x08: ("e", "E"), 0x09: ("f", "F"), 0x0A: ("g", "G"), 0x0B: ("h", "H"),
    0x0C: ("i", "I"), 0x0D: ("j", "J"), 0x0E: ("k", "K"), 0x0F: ("l", "L"),
    0x10: ("m", "M"), 0x11: ("n", "N"), 0x12: ("o", "O"), 0x13: ("p", "P"),
    0x14: ("q", "Q"), 0x15: ("r", "R"), 0x16: ("s", "S"), 0x17: ("t", "T"),
    0x18: ("u", "U"), 0x19: ("v", "V"), 0x1A: ("w", "W"), 0x1B: ("x", "X"),
    0x1C: ("y", "Y"), 0x1D: ("z", "Z"),
    0x1E: ("1", "!"), 0x1F: ("2", "@"), 0x20: ("3", "#"), 0x21: ("4", "$"),
    0x22: ("5", "%"), 0x23: ("6", "^"), 0x24: ("7", "&"), 0x25: ("8", "*"),
    0x26: ("9", "("), 0x27: ("0", ")"),
    0x2C: (" ", " "), 0x2D: ("-", "_"), 0x2E: ("=", "+"),
}
SHIFT = 0x22  # left (0x02) | right (0x20) shift bits

USBMON = struct.Struct("<QBBBBHbbqiiII8sIIII")  # 64-byte usbmon header


def packets(path):
    with open(path, "rb") as f:
        blob = f.read()
    magic, _, _, _, _, _, dlt = struct.unpack("<IHHiIII", blob[:24])
    assert magic == 0xa1b2c3d4, "not a little-endian pcap"
    assert dlt == 220, f"expected DLT 220 (usbmon mmapped), got {dlt}"
    off = 24
    while off + 16 <= len(blob):
        _, _, incl, _ = struct.unpack("<IIII", blob[off:off + 16])
        off += 16
        yield blob[off:off + incl]
        off += incl


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "capture.pcap"

    # Discover which device address speaks 8-byte reports (the keyboard).
    counts = {}
    parsed = []
    for data in packets(path):
        if len(data) < 64:
            continue
        fields = USBMON.unpack(data[:64])
        ptype, dev, len_cap = fields[1], fields[4], fields[12]
        report = data[64:64 + len_cap]
        parsed.append((ptype, dev, report))
        if len_cap == 8:
            counts[dev] = counts.get(dev, 0) + 1
    kbd = max(counts, key=counts.get)

    out = []
    for ptype, dev, report in parsed:
        if dev != kbd or ptype != ord('C') or len(report) != 8:
            continue
        mod, _, key = report[0], report[1], report[2]
        if key == 0:            # key release / modifier-only -> ignore
            continue
        if key not in HID:
            continue
        plain, shifted = HID[key]
        out.append(shifted if (mod & SHIFT) else plain)

    passphrase = "".join(out)
    print("device addresses with 8-byte reports:", counts, "-> keyboard =", kbd)
    print("passphrase:", passphrase)
    print("flag:      ", "CTF{" + passphrase + "}")


if __name__ == "__main__":
    main()
