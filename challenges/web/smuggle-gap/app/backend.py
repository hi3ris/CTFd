#!/usr/bin/env python3
"""backend.py -- the internal application, sitting BEHIND the edge proxy.

It binds to loopback only; in the deployed container nothing outside can reach
it directly. It speaks HTTP/1.1 with keep-alive and frames request bodies using
the app rules in framing.py (chunked-preferred). It exposes:

    GET  /                 public banner
    GET  /status           public health/status (has a debug-routing decoy)
    POST /submit           public: accept a "job" (used as the smuggle carrier)
    GET  /internal/flag    INTERNAL management route -- returns the team flag

The internal route trusts the network boundary: if a request reaches it, the
edge is assumed to have authorised it. That assumption is the whole game -- the
flag is emitted only when this route is genuinely reached, which (thanks to the
edge policy) is only possible via the framing gap.
"""
import json
import os
import socket
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framing import app_split_requests  # noqa: E402

try:
    from flag import get_flag  # when run from the challenge root
except Exception:  # pragma: no cover - path shim for `cd app && python backend.py`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from flag import get_flag

FLAG = get_flag()

HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
PORT = int(os.environ.get("BACKEND_PORT", "9000"))


def _resp(status: str, obj, keep_alive: bool = True) -> bytes:
    body = json.dumps(obj).encode("utf-8")
    lines = [
        f"HTTP/1.1 {status}",
        "Content-Type: application/json",
        f"Content-Length: {len(body)}",
        "Server: nimbus-appd/1.2",
        f"Connection: {'keep-alive' if keep_alive else 'close'}",
    ]
    return ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8") + body


def route(method: str, target: str, headers, body: bytes) -> bytes:
    path = target.split("?", 1)[0].split("#", 1)[0]

    if path == "/" and method == "GET":
        return _resp("200 OK", {
            "service": "nimbus internal appd",
            "note": "you are talking to the app tier; requests normally arrive "
                    "via the edge",
            "public_endpoints": ["GET /", "GET /status", "POST /submit"],
            "management_endpoints": ["GET /internal/flag"],
            "management_note": "management endpoints are not exposed at the edge",
        })

    if path == "/status" and method == "GET":
        # DECOY: a 'debug routing' knob that looks like it can re-target a
        # request internally. It only ECHOES the requested route; it never
        # dispatches to it and never yields the flag. Costs real effort to rule
        # out, but leads nowhere.
        debug_route = headers.get("x-debug-route")
        out = {"status": "ok", "queue_depth": 0, "app": "nimbus-appd/1.2"}
        if debug_route:
            out["debug_routing"] = "disabled in production"
            out["requested_route"] = debug_route
            out["dispatched"] = False
        return _resp("200 OK", out)

    if path == "/submit" and method == "POST":
        return _resp("200 OK", {
            "accepted": True,
            "bytes": len(body),
            "note": "job queued",
        })

    if path == "/internal/flag" and method == "GET":
        # The internal management route. Reaching this at all is the win: the
        # edge forbids it, so a request only lands here through the framing gap.
        return _resp("200 OK", {
            "route": "internal.flag",
            "granted": True,
            "message": "internal route reached -- the edge should never have "
                       "let this request through",
            "flag": FLAG,
        })

    return _resp("404 Not Found", {"error": "no such route", "path": path})


def handle(conn: socket.socket, addr) -> None:
    conn.settimeout(10.0)
    buf = b""
    try:
        while True:
            try:
                chunk = conn.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
            requests, consumed = app_split_requests(buf)
            if consumed:
                buf = buf[consumed:]
            for method, target, headers, body in requests:
                # Persist keep-alive so multiple pipelined/smuggled requests on
                # the SAME connection are all served in order.
                conn.sendall(route(method, target, headers, body))
    except (ConnectionError, OSError):
        pass
    finally:
        try:
            conn.close()
        except OSError:
            pass


def serve() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(64)
    print(f"[backend] internal app listening on {HOST}:{PORT}", flush=True)
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    serve()
