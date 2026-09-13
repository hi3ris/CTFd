#!/usr/bin/env python3
"""framing.py -- request framing primitives shared by the edge and the app.

This is the heart of the challenge. The edge proxy (front.py) and the internal
application (backend.py) are two independent HTTP/1.1 speakers on the same
keep-alive connection, and they DISAGREE about where one request ends and the
next begins:

    * The EDGE decides body length using Content-Length ONLY. It does not
      recognise the streaming/`Transfer-Encoding` framing at all -- to the edge
      it is just another opaque header that gets copied through verbatim.

    * The APP prefers the streaming/chunked framing whenever that header is
      present, and ignores Content-Length in that case.

When a single set of bytes satisfies BOTH interpretations differently, the edge
sees one request where the app sees two. The edge only ever authorises the ONE
request it can see, so the second (app-visible) request slips past the edge's
route policy. Everything below is deliberately small and self-contained -- it
is our own minimal framing, not any real product or CVE -- so the behaviour is
fully deterministic per instance.

All functions here are pure and import-safe, so they can be unit-tested without
binding a socket.
"""
from typing import Dict, List, Optional, Tuple

CRLF = b"\r\n"
HEADER_SEP = b"\r\n\r\n"


def parse_head(head: bytes) -> Tuple[str, str, str, Dict[str, str]]:
    """Parse a request head (through the blank line) into its pieces.

    Returns (method, target, version, headers) where headers is a lower-cased
    name -> value dict. Duplicate headers keep the FIRST occurrence (matches how
    both of our parsers behave; not security-relevant here).
    """
    lines = head.split(CRLF)
    request_line = lines[0].decode("latin-1")
    parts = request_line.split(" ")
    method = parts[0] if parts else ""
    target = parts[1] if len(parts) > 1 else "/"
    version = parts[2] if len(parts) > 2 else "HTTP/1.1"
    headers: Dict[str, str] = {}
    for line in lines[1:]:
        if not line:
            continue
        name, sep, value = line.partition(b":")
        if not sep:
            continue
        key = name.decode("latin-1").strip().lower()
        if key not in headers:
            headers[key] = value.decode("latin-1").strip()
    return method, target, version, headers


# ---------------------------------------------------------------------------
# EDGE framing (front.py): Content-Length only.
# ---------------------------------------------------------------------------
def edge_body_length(headers: Dict[str, str]) -> int:
    """How the EDGE sizes a body: Content-Length, or 0 if absent/garbage.

    The edge has no concept of chunked/streaming transfer. If a request also
    carries a `Transfer-Encoding` header the edge does NOT act on it -- it is
    copied downstream untouched.
    """
    raw = headers.get("content-length")
    if raw is None:
        return 0
    try:
        return int(raw.strip())
    except ValueError:
        return 0


def edge_take_one(buf: bytes) -> Optional[Tuple[str, str, Dict[str, str], int]]:
    """Parse exactly ONE request the way the edge does.

    Returns (method, target, headers, total_len) once `buf` holds a full
    request (head + Content-Length bytes), else None if more bytes are needed.
    `total_len` is how many bytes of `buf` belong to this single edge-request --
    which, in a smuggling payload, also swallows the hidden second request.
    """
    sep = buf.find(HEADER_SEP)
    if sep == -1:
        return None
    head_end = sep + len(HEADER_SEP)
    method, target, _version, headers = parse_head(buf[:head_end])
    total = head_end + edge_body_length(headers)
    if total > len(buf):
        return None
    return method, target, headers, total


# ---------------------------------------------------------------------------
# APP framing (backend.py): chunked-preferred, otherwise Content-Length.
# ---------------------------------------------------------------------------
def _read_chunked(buf: bytes, start: int) -> Optional[int]:
    """Return the index just past a chunked body beginning at `start`.

    Minimal chunked reader: sizes in hex, terminated by a 0-length chunk
    followed by the final CRLF. No trailer support (kept deterministic). Returns
    None if the body is not yet complete / malformed.
    """
    i = start
    while True:
        nl = buf.find(CRLF, i)
        if nl == -1:
            return None
        size_field = buf[i:nl].split(b";", 1)[0].strip()
        try:
            size = int(size_field, 16)
        except ValueError:
            return None
        i = nl + 2
        if size == 0:
            # terminating chunk -> expect the closing CRLF right here
            if buf[i:i + 2] == CRLF:
                return i + 2
            return None
        i += size
        if buf[i:i + 2] != CRLF:
            return None
        i += 2


def app_split_requests(buf: bytes) -> Tuple[List[Tuple[str, str, Dict[str, str], bytes]], int]:
    """Parse as many complete requests as `buf` contains, the way the APP does.

    THE DISCREPANCY: when a request carries `Transfer-Encoding: chunked` the app
    frames its body with the chunked reader and ignores Content-Length; only
    otherwise does it fall back to Content-Length. Because a smuggling payload's
    edge-body is itself a valid (empty) chunked body plus a second request, the
    app yields TWO requests where the edge yielded one.

    Returns (requests, consumed) where each request is
    (method, target, headers, body_bytes) and `consumed` is how many bytes of
    `buf` were framed into complete requests.
    """
    requests: List[Tuple[str, str, Dict[str, str], bytes]] = []
    pos = 0
    n = len(buf)
    while pos < n:
        sep = buf.find(HEADER_SEP, pos)
        if sep == -1:
            break
        head_end = sep + len(HEADER_SEP)
        method, target, _version, headers = parse_head(buf[pos:head_end])
        te = headers.get("transfer-encoding", "").lower()
        if "chunked" in te:
            body_end = _read_chunked(buf, head_end)
            if body_end is None:
                break
        else:
            raw = headers.get("content-length")
            try:
                cl = int(raw.strip()) if raw is not None else 0
            except ValueError:
                cl = 0
            body_end = head_end + cl
            if body_end > n:
                break
        requests.append((method, target, headers, buf[head_end:body_end]))
        pos = body_end
    return requests, pos
