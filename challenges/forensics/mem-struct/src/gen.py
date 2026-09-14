#!/usr/bin/env python3
"""Generate ``memdump.bin`` for the mem-struct challenge.

A raw memory dump (64 KiB of pseudo-random bytes). Somewhere inside sits a
16-byte ``secret_record`` struct (little-endian):

    offset  0  uint32 magic     = 0x0FF5E7ED
    offset  4  uint32 xor_key
    offset  8  uint32 flag_off   (absolute offset of the flag bytes in the dump)
    offset 12  uint32 flag_len

The flag bytes at ``flag_off`` are stored XOR-obfuscated with the 4-byte
little-endian ``xor_key`` (repeating), so ``strings`` alone will not find them.
A single plaintext decoy flag is planted to mislead a lazy ``strings`` sweep.
"""
import random
import struct

FLAG = "NCTF{struct_0ffs3t_p01nt3r_ch4s3}"
DECOY = "NCTF{run_str1ngs_and_h0p3_n0t_th3_fl4g}"

MAGIC = 0x0FF5E7ED
SIZE = 64 * 1024

random.seed(0xC0FFEE)


def main() -> None:
    buf = bytearray(random.getrandbits(8) for _ in range(SIZE))

    # plaintext decoy (allowed: exactly one)
    d_off = 0x1200
    buf[d_off : d_off + len(DECOY)] = DECOY.encode()

    # obfuscated real flag
    xor_key = 0x5A6B3C1D
    key_bytes = struct.pack("<I", xor_key)
    flag_bytes = FLAG.encode()
    obf = bytes(b ^ key_bytes[i % 4] for i, b in enumerate(flag_bytes))
    flag_off = 0xB840
    buf[flag_off : flag_off + len(obf)] = obf

    # the struct
    record = struct.pack("<IIII", MAGIC, xor_key, flag_off, len(flag_bytes))
    rec_off = 0x74C0
    buf[rec_off : rec_off + len(record)] = record

    with open("memdump.bin", "wb") as fh:
        fh.write(buf)
    print(
        f"wrote memdump.bin ({len(buf)} bytes); record@{rec_off:#x} "
        f"flag@{flag_off:#x}; flag={FLAG}"
    )


if __name__ == "__main__":
    main()
