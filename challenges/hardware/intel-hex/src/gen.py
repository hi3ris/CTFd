#!/usr/bin/env python3
"""Generate an Intel HEX dump of a microcontroller memory image.

The flag lives at a fixed offset in the reconstructed memory, but each byte is
stored with its two nibbles swapped (e.g. 'N' = 0x4E is stored as 0xE4). The
rest of memory is filled with plausible-looking filler.

Intel HEX record: :LL AAAA TT [DD..] CC
  LL  data byte count
  AAAA 16-bit address
  TT  record type (00 = data, 01 = EOF)
  CC  checksum = two's complement of the sum of all prior bytes
"""

import os

FLAG = b"NCTF{intel_hex_offset_nibble_swap}"
FLAG_OFFSET = 0x0040
IMAGE_SIZE = 0x0100


def swap_nibbles(b):
    return ((b << 4) & 0xF0) | ((b >> 4) & 0x0F)


def hex_record(addr, data, rectype=0x00):
    body = [len(data), (addr >> 8) & 0xFF, addr & 0xFF, rectype] + list(data)
    checksum = (-sum(body)) & 0xFF
    body.append(checksum)
    return ":" + "".join("{:02X}".format(x) for x in body)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, os.pardir, "image.hex")

    # deterministic filler
    mem = bytearray()
    x = 0x3C
    for _ in range(IMAGE_SIZE):
        x = (x * 5 + 0x1B) & 0xFF
        mem.append(x)

    # place the nibble-swapped flag at the fixed offset
    for i, ch in enumerate(FLAG):
        mem[FLAG_OFFSET + i] = swap_nibbles(ch)

    lines = []
    for addr in range(0, IMAGE_SIZE, 16):
        lines.append(hex_record(addr, mem[addr : addr + 16]))
    lines.append(":00000001FF")  # EOF record

    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")

    print("wrote", os.path.abspath(out), "records:", len(lines))


if __name__ == "__main__":
    main()
