#!/usr/bin/env python3
"""Producer for reset-token-lcg artifacts (reset log + sealed flag)."""

import datetime
import hashlib

A = 1664525
C = 1013904223
M = 2**32
FLAG = "NCTF{predictable_reset_token_from_seeded_prng}"


def make_token(seed: int) -> str:
    state = seed % M
    parts = []
    for _ in range(4):
        state = (A * state + C) % M
        parts.append("%08x" % state)
    return "".join(parts)


def keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


def epoch(y, mo, d, h, mi, s) -> int:
    return int(
        datetime.datetime(y, mo, d, h, mi, s, tzinfo=datetime.timezone.utc).timestamp()
    )


def iso(t: int) -> str:
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def main() -> None:
    guests = [
        ("kojo", epoch(2026, 9, 14, 10, 22, 1)),
        ("ama", epoch(2026, 9, 14, 10, 22, 3)),
        ("efua", epoch(2026, 9, 14, 10, 23, 15)),
    ]
    admin_ts = epoch(2026, 9, 14, 10, 23, 47)
    lines = [
        f"{iso(t)}  user={n}  reset token issued: {make_token(t)}" for n, t in guests
    ]
    lines.append(
        f"{iso(admin_ts)}  user=admin  reset token issued: (emailed to admin, not logged)"
    )
    print("\n".join(lines))
    key = hashlib.sha256(b"resetseal|" + make_token(admin_ts).encode()).digest()
    ct = bytes(a ^ b for a, b in zip(FLAG.encode(), keystream(key, len(FLAG))))
    print("SEALED_FLAG_HEX =", ct.hex())


if __name__ == "__main__":
    main()
