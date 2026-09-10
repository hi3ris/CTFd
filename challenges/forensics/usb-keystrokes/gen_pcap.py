#!/usr/bin/env python3
"""
gen_pcap.py - scripted generator for the usb-keystrokes challenge.

Produces `capture.pcap`, a Linux usbmon (LINKTYPE_USB_LINUX_MMAPPED / DLT 220)
capture that Wireshark/tshark parse as USB URBs. The capture contains:

  * A USB keyboard (device address 3, interrupt-IN endpoint 0x81) typing the
    challenge passphrase, emitted as realistic SUBMIT('S')/COMPLETE('C') URB
    pairs. Only the COMPLETE packets carry the 8-byte HID boot-keyboard report
    [modifier, reserved, key1..key6].  Key-release reports (all zero) are
    interleaved, exactly as a real device sends them.

  * A USB mouse (device address 5, interrupt-IN endpoint 0x82, 4-byte reports)
    generating random motion noise the whole time.  This is the DECOY: a naive
    "dump every interrupt capdata byte" solve mixes mouse bytes into the text
    and produces garbage.  It is refutable in seconds - the mouse lives on a
    different device address and its reports are 4 bytes, not 8.

Nothing here hand-fakes the HID semantics: the report bytes are built from the
real USB HID Usage Table (keyboard/keypad page 0x07) and the standard boot
keyboard report layout, then serialised through the genuine usbmon header
struct. Re-running this script reproduces the byte-identical pcap.
"""
import struct
import random

# ---------------------------------------------------------------------------
# The passphrase that is "typed" on the keyboard. The flag is this string
# wrapped in CTF{...}.  Keep it in sync with challenge.yml / flag.py.
# ---------------------------------------------------------------------------
PASSPHRASE = "Bl4ck_H4t_USB_2026"

# USB HID Usage Table, Keyboard/Keypad Page (0x07). Maps the *unshifted* and
# *shifted* character each usage code produces on a US layout.
#   usage : (plain_char, shifted_char)
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
    0x2C: (" ", " "),
    0x2D: ("-", "_"), 0x2E: ("=", "+"),
}

# Build the reverse map: character -> (usage_code, needs_shift)
CHAR2HID = {}
for usage, (plain, shifted) in HID.items():
    CHAR2HID.setdefault(plain, (usage, False))
    CHAR2HID.setdefault(shifted, (usage, True))

MOD_LSHIFT = 0x02

# usbmon mmapped header is a fixed 64-byte little-endian struct.
_USBMON = struct.Struct("<QBBBBHbbqiiII8sIIII")
assert _USBMON.size == 64


def usbmon_record(ts, urb_id, ptype, epnum, devnum, data):
    """Serialise one usbmon URB (64-byte header + captured data) into a
    (record-header + payload) pcap record blob.

    ptype   : b'S' submit or b'C' complete
    epnum   : full endpoint address incl. direction bit (0x81 == IN ep1)
    devnum  : USB device address
    data    : bytes actually captured for this URB (may be empty)
    """
    xfer_type = 1                      # 1 == interrupt transfer
    length = len(data)                 # requested URB data length
    len_cap = len(data)                # bytes present in the file
    hdr = _USBMON.pack(
        urb_id,                        # u64 id
        ord(ptype),                    # u8  event type ('S'/'C')
        xfer_type,                     # u8  transfer type
        epnum,                         # u8  endpoint
        devnum,                        # u8  device address
        1,                             # u16 bus number
        ord('-'),                      # s8  flag_setup ('-' == not present)
        ord('<') if epnum & 0x80 else ord('>'),  # s8 flag_data
        int(ts),                       # s64 ts_sec
        int((ts - int(ts)) * 1_000_000),  # s32 ts_usec
        0,                             # s32 status (0 == success)
        length,                        # u32 urb length
        len_cap,                       # u32 captured length
        b"\x00" * 8,                   # setup packet (unused for interrupt)
        1,                             # u32 interval
        0,                             # u32 start_frame
        0,                             # u32 transfer flags
        0,                             # u32 number of iso descriptors
    )
    payload = hdr + data
    rec = struct.pack("<IIII", int(ts), int((ts - int(ts)) * 1_000_000),
                      len(payload), len(payload)) + payload
    return rec


def kbd_report(usage, shift):
    """8-byte boot keyboard report holding a single key (+ optional shift)."""
    mod = MOD_LSHIFT if shift else 0x00
    return bytes([mod, 0x00, usage, 0, 0, 0, 0, 0])


KBD_RELEASE = bytes(8)  # all keys up


def main():
    random.seed(0xC0FFEE)              # deterministic output
    records = []
    urb = 0xffff880000000000
    t = 1_700_000_000.000000          # base capture timestamp

    def emit(ptype, epnum, devnum, data):
        nonlocal urb, t
        records.append(usbmon_record(t, urb, ptype, epnum, devnum, data))
        urb += 1
        t += 0.001                    # 1 ms between URBs

    def mouse_noise(n=1):
        # decoy device: 4-byte relative mouse reports on dev 5, ep 0x82
        for _ in range(n):
            btn = random.choice([0, 0, 0, 1])
            dx = random.randint(-6, 6) & 0xff
            dy = random.randint(-6, 6) & 0xff
            emit('S', 0x82, 5, b"")
            emit('C', 0x82, 5, bytes([btn, dx, dy, 0x00]))

    mouse_noise(3)
    for ch in PASSPHRASE:
        if ch not in CHAR2HID:
            raise ValueError(f"passphrase char {ch!r} has no HID mapping")
        usage, shift = CHAR2HID[ch]
        # key down: submit (no data captured) then complete (report present)
        emit('S', 0x81, 3, b"")
        emit('C', 0x81, 3, kbd_report(usage, shift))
        mouse_noise(random.randint(0, 2))
        # key up
        emit('S', 0x81, 3, b"")
        emit('C', 0x81, 3, KBD_RELEASE)
        mouse_noise(random.randint(0, 2))
    mouse_noise(4)

    # pcap global header: LINKTYPE_USB_LINUX_MMAPPED == 220
    ghdr = struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 220)
    with open("capture.pcap", "wb") as f:
        f.write(ghdr)
        for r in records:
            f.write(r)

    print(f"wrote capture.pcap  ({len(records)} URBs)")
    print(f"passphrase = {PASSPHRASE}")
    print(f"flag       = CTF{{{PASSPHRASE}}}")


if __name__ == "__main__":
    main()
