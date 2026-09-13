#!/usr/bin/env python3
"""
Reference solver for padding-oracle-lite.

Speaks the POP1 binary framing, pulls the token ciphertext, runs a CBC padding
oracle attack against the VERIFY opcode to recover the plaintext, strips PKCS#7,
and SUBMITs the recovered token to receive the per-team flag.

Usage:
    python3 solve.py <host> <port>
    python3 solve.py            # defaults to 127.0.0.1 9007
"""
import socket
import struct
import sys

SYNC = 0xAA
OP_GETCT = 0x10
OP_CT = 0x12
OP_VERIFY = 0x20
OP_STATUS = 0x21
OP_SUBMIT = 0x30
OP_FLAG = 0x31
OP_NOPE = 0x32
BLOCK = 16


def build_frame(opcode, payload=b""):
    if len(payload) % 2:
        payload += b"\x00"
    nwords = len(payload) // 2
    chk = opcode
    for b in payload:
        chk ^= b
    return bytes([SYNC, opcode]) + struct.pack("<H", nwords) + payload + bytes([chk & 0xFF])


def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            raise ConnectionError("closed")
        buf += c
    return buf


def read_frame(sock):
    assert recv_exact(sock, 1)[0] == SYNC, "bad sync"
    opcode = recv_exact(sock, 1)[0]
    nwords = struct.unpack("<H", recv_exact(sock, 2))[0]
    payload = recv_exact(sock, nwords * 2)
    recv_exact(sock, 1)  # checksum (trusted)
    return opcode, payload


def oracle(sock, blob):
    """Return True iff VERIFY reports code 1 for this IV||CT blob."""
    sock.sendall(build_frame(OP_VERIFY, blob))
    op, payload = read_frame(sock)
    assert op == OP_STATUS, f"unexpected op {op:#x}"
    return struct.unpack(">H", payload)[0] == 1


def recover_block(sock, prev, target):
    """Recover the 16 intermediate bytes I = D_K(target), then plaintext =
    I XOR prev. Classic byte-at-a-time padding oracle on one block."""
    inter = bytearray(16)
    for pad in range(1, 17):
        pos = 16 - pad
        forged = bytearray(16)
        for k in range(pos + 1, 16):
            forged[k] = inter[k] ^ pad
        found = False
        for guess in range(256):
            forged[pos] = guess
            if oracle(sock, bytes(forged) + target):
                # Guard against the false positive at pad==1 where an existing
                # trailing byte accidentally forms valid padding of a longer run.
                if pad == 1:
                    probe = bytearray(forged)
                    probe[pos - 1] ^= 0xFF
                    if not oracle(sock, bytes(probe) + target):
                        continue
                inter[pos] = guess ^ pad
                found = True
                break
        if not found:
            raise RuntimeError(f"no valid byte at pad={pad}")
    return bytes(a ^ b for a, b in zip(inter, prev))


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9007

    sock = socket.create_connection((host, port), timeout=30)
    op, banner = read_frame(sock)  # banner
    print("[*] banner:", banner.decode(errors="replace").strip())

    sock.sendall(build_frame(OP_GETCT))
    op, blob = read_frame(sock)
    assert op == OP_CT
    print(f"[*] token blob: {len(blob)} bytes (IV + {len(blob) - 16} ct)")

    blocks = [blob[i:i + BLOCK] for i in range(0, len(blob), BLOCK)]
    plaintext = b""
    for i in range(1, len(blocks)):
        pt = recover_block(sock, blocks[i - 1], blocks[i])
        plaintext += pt
        print(f"[*] recovered block {i}: {pt!r}")

    # strip PKCS#7
    n = plaintext[-1]
    token = plaintext[:-n]
    print(f"[+] recovered token: {token!r}")

    sock.sendall(build_frame(OP_SUBMIT, token))
    op, payload = read_frame(sock)
    if op == OP_FLAG:
        print("[+] FLAG:", payload.decode(errors="replace").strip())
    else:
        print("[-] rejected:", payload.decode(errors="replace"))
        sys.exit(1)


if __name__ == "__main__":
    main()
