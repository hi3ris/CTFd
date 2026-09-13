#!/usr/bin/env python3
"""
Static solver for 'strings-lie'.

We never run the binary. We recover the answer purely from its bytes:

  1. The check applies an invertible per-byte transform to the passphrase P
     and compares it to an embedded array target[]:
         t[i] = ((P[i] ^ 0x5A) + (i*7 + 3)) & 0xFF
     which inverts to:
         P[i] = ((t[i] - (i*7 + 3)) & 0xFF) ^ 0x5A
  2. The real flag is stored XORed with P repeated (flag_enc[i] = flag[i] ^ P[i % len]).

So: find the 23-byte window in the binary whose inverse-transform is a clean
ASCII passphrase, then find the window that decrypts under it to a NCTF{...}
string. Both arrays live in .rodata; we just brute-force the two window positions.
No answer is hardcoded -- this survives a rebuild with a different key/flag.

The flag length is discovered, not assumed: we anchor on a window that decrypts
to "NCTF{" and extend to the closing "}". (A previous version hardcoded a
30-byte flag and silently failed on the real 31-byte flag.)

Usage: python3 solve.py [path-to-chall]
"""
import sys, string

PLEN = 23        # length of the passphrase / target[]
FLAG_MAX = 64    # upper bound while scanning for the closing brace
PRINTABLE = set(bytes(string.ascii_letters + string.digits + "_{}!?-", "ascii"))

def invert(window):
    return bytes(((window[i] - (i * 7 + 3)) & 0xFF) ^ 0x5A for i in range(PLEN))

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../chall"
    data = open(path, "rb").read()

    # 1) candidate passphrases: every PLEN-window that inverts to clean ASCII
    candidates = []
    for off in range(len(data) - PLEN):
        p = invert(data[off:off + PLEN])
        if all(c in PRINTABLE for c in p):
            candidates.append(p)

    # 2) for each candidate key, find a window that decrypts to NCTF{...} of ANY
    #    length: anchor on the "NCTF{" prefix, then extend to the closing "}".
    for p in candidates:
        for off in range(len(data) - 5):
            head = bytes(data[off + i] ^ p[i % PLEN] for i in range(5))
            if head != b"NCTF{":
                continue
            out = bytearray(head)
            for i in range(5, FLAG_MAX):
                if off + i >= len(data):
                    break
                c = data[off + i] ^ p[i % PLEN]
                if not (32 <= c < 127):
                    break
                out.append(c)
                if c == ord("}"):
                    print("passphrase :", p.decode())
                    print("flag       :", out.decode())
                    return
    print("no solution found", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
