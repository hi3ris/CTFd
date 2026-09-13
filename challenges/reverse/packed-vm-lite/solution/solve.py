#!/usr/bin/env python3
"""
Solver for packed-vm-lite.

Once the VM opcodes are read, the validation of each serial byte i is:

    amt = (i*3 + 1) & 7
    t   = rotl8(serial[i], amt)
    t  ^= KEY[i]
    t   = (t + prev) & 0xFF
    require t == TARGET[i]
    prev = serial[i]              # feedback uses the raw plaintext byte
    (prev seeded to 0x5A)

That inverts cleanly and sequentially:

    t  = (TARGET[i] - prev) & 0xFF
    t ^= KEY[i]
    serial[i] = rotr8(t, amt)
    prev = serial[i]

KEY[] and TARGET[] are the tables embedded in the binary. This solver hardcodes
them (as recovered from the ELF's .rodata) so it stands alone; it optionally
verifies against the real binary if a path is given.

Usage:
    python3 solve.py            # print the serial / flag
    python3 solve.py ../vmcheck # also run the binary to confirm
"""
import subprocess, sys

KEY = [0x5d,0x02,0x2f,0xc8,0xf9,0x9e,0xb3,0x6c,0x15,0x3a,0xc7,0xe0,
       0x81,0xa6,0x7b,0x14,0x0d,0xf2,0xdf,0xb8,0x69,0x4e,0x23,0x1c]
TARGET = [0x0b,0x4a,0xed,0xa0,0x38,0x63,0x0c,0x19,0xd8,0xac,0xd9,0x02,
          0x06,0x06,0xf4,0xee,0xdb,0xe5,0xe4,0x78,0x57,0x70,0x72,0xb8]
SEED = 0x5A

def rotr8(v, n):
    n &= 7
    return ((v >> n) | (v << (8 - n))) & 0xFF

def solve():
    prev = SEED
    out = []
    for i in range(24):
        amt = (i * 3 + 1) & 7
        t = (TARGET[i] - prev) & 0xFF
        t ^= KEY[i]
        c = rotr8(t, amt)
        out.append(c)
        prev = c               # feedback on the recovered plaintext byte
    return bytes(out)

def main():
    serial = solve()
    print("serial:", serial.decode())
    print("flag:  NCTF{%s}" % serial.decode())
    if len(sys.argv) > 1:
        bin_path = sys.argv[1]
        r = subprocess.run([bin_path], input=serial + b"\n",
                           capture_output=True)
        out = r.stdout.decode(errors="replace")
        print("--- binary says ---")
        print(out.strip())
        assert "Correct!" in out, "binary did not accept the serial!"
        print("[+] verified against binary")

if __name__ == "__main__":
    main()
