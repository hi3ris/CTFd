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
ASCII passphrase, then find the 30-byte window that decrypts under it to a NCTF{...}
string. Both arrays live in .rodata; we just brute-force the two window positions.
No answer is hardcoded -- this survives a rebuild with a different key/flag.

Usage: python3 solve.py [path-to-chall]
"""
import sys, string

PLEN = 23      # length of the passphrase / target[]
FLEN = 30      # length of flag_enc[] (len("NCTF{...}"))
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

    # 2) for each candidate key, look for a flag_enc window decrypting to NCTF{...}
    for p in candidates:
        for off in range(len(data) - FLEN):
            w = data[off:off + FLEN]
            flag = bytes(w[i] ^ p[i % PLEN] for i in range(FLEN))
            if flag.startswith(b"NCTF{") and flag.endswith(b"}") and \
               all(32 <= c < 127 for c in flag):
                print("passphrase :", p.decode())
                print("flag       :", flag.decode())
                return
    print("no solution found", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
