#!/usr/bin/env python3
"""
padding-oracle-lite -- a per-team CBC padding oracle served over a small,
home-grown BINARY protocol (POP1). It is deliberately NOT HTTP: stock tools
(padbuster, a Burp plugin, `curl`) have nothing to talk to. You must speak the
framing yourself.

What the service will and will not do:
  * It hands you an encrypted session token on request (opcode GETCT). The
    token plaintext is random per instance; it is NOT recoverable from the
    ciphertext without the server.
  * It exposes a VERIFY opcode: you send it an IV||ciphertext blob, it decrypts
    with the instance key and returns a 1-word status code. The service does
    NOT tell you what the code *means* -- discovering that is the challenge.
  * It emits the flag ONLY after you SUBMIT the exact recovered token plaintext.
    Nothing here is a downloadable flag: the running service is the oracle, and
    it verifies the EFFECT (you produced the real plaintext), not any particular
    method or payload shape.

Framing (POP1), see handout/SPEC.md for the partial spec players get:

    offset 0 : 0xAA               sync byte
    offset 1 : opcode  (1 byte)
    offset 2 : length  (2 bytes, little-endian) = number of 2-byte WORDS
                                                   in the payload (NOT bytes)
    offset 4 : payload (length*2 bytes)
    last     : checksum (1 byte) = XOR of the opcode byte and every payload byte

Every payload is an even number of bytes so the word count is exact.
"""
import os
import socketserver
import struct
import threading

from Crypto.Cipher import AES

from flag import get_flag

# ---------------------------------------------------------------------------
# Flag source. The platform now injects PER-CHALLENGE values (FLAG /
# CHALLENGE_SECRET) at container-creation time, NOT the team master secret.
# The flag is resolved through flag.get_flag(); TEAM_SECRET is no longer read
# on the arena (get_flag only falls back to it for off-arena local dev). None
# of these values are present in any file a player can download.
# ---------------------------------------------------------------------------

# The AES-128-CBC key + IV are fresh per instance. The key never leaves the
# process; brute forcing it is not the intended path and is not feasible.
KEY = os.urandom(16)
IV = os.urandom(16)


def compute_flag() -> str:
    return get_flag()


# ---------------------------------------------------------------------------
# The session token. 32 bytes (two AES blocks of real data) so recovery needs a
# genuine multi-block padding-oracle attack, not a single-block special case.
# Random per instance -> cannot be guessed; must be decrypted through the oracle.
# ---------------------------------------------------------------------------
TOKEN = ("SESSION_" + os.urandom(12).hex()).encode()  # 8 + 24 = 32 bytes
assert len(TOKEN) == 32


def pkcs7_pad(data: bytes, block: int = 16) -> bytes:
    n = block - (len(data) % block)
    return data + bytes([n]) * n


def pkcs7_ok(data: bytes, block: int = 16) -> bool:
    if not data or len(data) % block != 0:
        return False
    n = data[-1]
    if n < 1 or n > block:
        return False
    return data[-n:] == bytes([n]) * n


# Precompute the ciphertext the service will hand out: IV || CT.
_CT = AES.new(KEY, AES.MODE_CBC, IV).encrypt(pkcs7_pad(TOKEN))
TOKEN_BLOB = IV + _CT  # 16 + 48 = 64 bytes


# ---------------------------------------------------------------------------
# POP1 framing.
# ---------------------------------------------------------------------------
SYNC = 0xAA

OP_BANNER = 0x11   # server -> client (on connect)
OP_GETCT = 0x10    # client -> server : request token ciphertext
OP_CT = 0x12       # server -> client : IV||CT
OP_VERIFY = 0x20   # client -> server : IV||CT to test
OP_STATUS = 0x21   # server -> client : 1 word status code
OP_SUBMIT = 0x30   # client -> server : recovered plaintext token
OP_FLAG = 0x31     # server -> client : the flag
OP_NOPE = 0x32     # server -> client : wrong token
OP_ERR = 0xEE      # server -> client : protocol/usage error (ascii reason)


def build_frame(opcode: int, payload: bytes = b"") -> bytes:
    if len(payload) % 2 != 0:
        payload += b"\x00"  # keep word alignment; never happens for our frames
    nwords = len(payload) // 2
    chk = opcode
    for b in payload:
        chk ^= b
    return bytes([SYNC, opcode]) + struct.pack("<H", nwords) + payload + bytes([chk & 0xFF])


def recv_exact(sock, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("peer closed")
        buf += chunk
    return buf


def read_frame(sock):
    """Return (opcode, payload) or raise ConnectionError. Raises ValueError on
    a malformed frame (bad sync / checksum)."""
    sync = recv_exact(sock, 1)[0]
    if sync != SYNC:
        raise ValueError("bad sync")
    opcode = recv_exact(sock, 1)[0]
    nwords = struct.unpack("<H", recv_exact(sock, 2))[0]
    payload = recv_exact(sock, nwords * 2)
    chk = recv_exact(sock, 1)[0]
    calc = opcode
    for b in payload:
        calc ^= b
    if (calc & 0xFF) != chk:
        raise ValueError("bad checksum")
    return opcode, payload


# ---------------------------------------------------------------------------
# Connection handler.
# ---------------------------------------------------------------------------
BANNER = (
    b"POP1 padding-oracle-lite. framing: 0xAA|op|len16le(words)|payload|xorck. "
    b"ops: GETCT=0x10 VERIFY=0x20 SUBMIT=0x30. token=32B ascii. "
    b"note: legacy default token was SESSION_000000000000000000000000 "
    b"(no longer in use)."
)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        sock = self.request
        sock.settimeout(120)
        # pad banner to even length for word alignment
        banner = BANNER if len(BANNER) % 2 == 0 else BANNER + b" "
        sock.sendall(build_frame(OP_BANNER, banner))

        while True:
            try:
                opcode, payload = read_frame(sock)
            except ValueError as e:
                try:
                    sock.sendall(build_frame(OP_ERR, self._pad(str(e).encode())))
                except OSError:
                    pass
                continue
            except (ConnectionError, OSError):
                return

            try:
                if opcode == OP_GETCT:
                    sock.sendall(build_frame(OP_CT, TOKEN_BLOB))

                elif opcode == OP_VERIFY:
                    code = self._verify(payload)
                    # status returned as a single 2-byte word, big-endian-ish:
                    # 0x0001 = "code 1", 0x0000 = "code 0". Meaning undocumented.
                    sock.sendall(build_frame(OP_STATUS, struct.pack(">H", code)))

                elif opcode == OP_SUBMIT:
                    if payload == TOKEN:
                        sock.sendall(build_frame(OP_FLAG, self._pad(compute_flag().encode())))
                    else:
                        sock.sendall(build_frame(OP_NOPE, self._pad(b"wrong token")))

                else:
                    sock.sendall(build_frame(OP_ERR, self._pad(b"unknown opcode")))
            except (ConnectionError, OSError):
                return

    @staticmethod
    def _pad(b: bytes) -> bytes:
        return b if len(b) % 2 == 0 else b + b"\x00"

    @staticmethod
    def _verify(blob: bytes) -> int:
        """The oracle. Returns 1 iff the decrypted plaintext has valid PKCS#7
        padding, else 0. The protocol does not tell the player this -- they must
        infer it. Malformed lengths -> 0 (indistinguishable from bad padding)."""
        if len(blob) < 32 or len(blob) % 16 != 0:
            return 0
        iv, ct = blob[:16], blob[16:]
        pt = AES.new(KEY, AES.MODE_CBC, iv).decrypt(ct)
        return 1 if pkcs7_ok(pt) else 0


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    host = os.environ.get("BIND_HOST", "0.0.0.0")
    port = int(os.environ.get("BIND_PORT", "9007"))
    srv = ThreadedTCPServer((host, port), Handler)
    print(f"padding-oracle-lite listening on {host}:{port}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
