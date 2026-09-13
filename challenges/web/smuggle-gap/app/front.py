#!/usr/bin/env python3
"""front.py -- the edge proxy. This is the only tier exposed to players.

It enforces a route policy: management routes (anything under /internal) are
FORBIDDEN at the edge and answered with 403 without ever touching the app tier.
Everything else is forwarded to the internal app over a keep-alive connection,
and the app's response(s) are relayed back.

The policy is applied to the ONE request the edge can see -- the request it
frames with Content-Length (see framing.edge_take_one). The edge has no notion
of chunked/streaming transfer, so it copies such requests downstream verbatim.
Its path check is hardened against the usual normalisation tricks (case,
percent-encoding, `.`/`..`, `//`, backslashes) so that the only bytes that ever
reach /internal are ones the edge could not see as /internal in the first
place.
"""
import os
import socket
import sys
import threading
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framing import edge_take_one  # noqa: E402

LISTEN_HOST = os.environ.get("FRONT_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("FRONT_PORT", "8080"))
BACKEND_HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "9000"))

# How long the edge keeps draining the app's keep-alive connection with no new
# bytes before it considers the exchange complete. Deterministic, not a race.
FORWARD_IDLE_S = float(os.environ.get("FORWARD_IDLE_S", "0.6"))


def normalize_path(target: str) -> str:
    """Aggressively normalise a request target to a canonical lowercase path.

    Defeats case tricks, repeated percent-encoding, `.`/`..` traversal, `//`
    runs and backslashes -- so naive attempts to sneak `/internal` past the ACL
    in the visible request line simply do not work.
    """
    path = target.split("?", 1)[0].split("#", 1)[0]
    prev = None
    while prev != path:  # collapse nested percent-encoding (e.g. %252f)
        prev = path
        path = urllib.parse.unquote(path)
    path = path.replace("\\", "/")
    segments = []
    for seg in path.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if segments:
                segments.pop()
            continue
        segments.append(seg)
    return ("/" + "/".join(segments)).lower()


def acl_forbidden(target: str) -> bool:
    norm = normalize_path(target)
    return norm == "/internal" or norm.startswith("/internal/")


def _forbidden_response() -> bytes:
    body = b'{"edge":"forbidden","detail":"management route not exposed at the edge"}'
    head = (
        "HTTP/1.1 403 Forbidden\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Server: nimbus-edge/3.0\r\n"
        "Connection: close\r\n\r\n"
    ).encode("utf-8")
    return head + body


def handle_client(csock: socket.socket) -> None:
    csock.settimeout(10.0)
    buf = b""
    try:
        parsed = None
        while parsed is None:
            try:
                chunk = csock.recv(65536)
            except socket.timeout:
                return
            if not chunk:
                return
            buf += chunk
            parsed = edge_take_one(buf)

        method, target, _headers, total = parsed
        raw = buf[:total]  # exactly the bytes the edge attributes to this request

        if acl_forbidden(target):
            csock.sendall(_forbidden_response())
            return

        # Forward the edge-request verbatim to the internal app and relay back
        # whatever the app produces (which, for a framing-gap payload, is more
        # than one response).
        try:
            bsock = socket.create_connection((BACKEND_HOST, BACKEND_PORT), timeout=5)
        except OSError:
            csock.sendall(
                b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n"
                b"Connection: close\r\n\r\n"
            )
            return
        try:
            bsock.sendall(raw)
            bsock.settimeout(FORWARD_IDLE_S)
            while True:
                try:
                    data = bsock.recv(65536)
                except socket.timeout:
                    break
                if not data:
                    break
                csock.sendall(data)
        finally:
            bsock.close()
    except (ConnectionError, OSError):
        pass
    finally:
        try:
            csock.close()
        except OSError:
            pass


def serve() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((LISTEN_HOST, LISTEN_PORT))
    srv.listen(128)
    print(f"[front] edge proxy listening on {LISTEN_HOST}:{LISTEN_PORT} "
          f"-> app {BACKEND_HOST}:{BACKEND_PORT}", flush=True)
    while True:
        conn, _addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    serve()
