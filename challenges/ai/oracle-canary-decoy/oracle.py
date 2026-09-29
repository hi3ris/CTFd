#!/usr/bin/env python3
"""ChannelBot -- an oracle with a canary decoy (offline stub).

This module deterministically mimics an assistant that answers over "channels".
Ordinary requests for the secret get a *decoy* flag -- a canary planted to catch
lazy submissions. The real flag is only served on the privileged admin channel,
which is unlocked by an ``X-Auth`` header carrying a maintenance token. That
token is stored obfuscated in this file; recover it to enter the admin channel.

Public API:  respond(prompt: str) -> str
"""

import base64

# Real flag: base64( reverse(flag) ).  Decoy flag: same scheme.
_REAL = "fWwzbm40aGNfbjFtZDRfbjFfczN2MWxfZzRsZl9sNDNye0ZUQ04="
_DECOY = "fWduMWswMGxfcDMza195MGMzZF80X3lsbjBfczFfczFodHtGVENO"
_TOK = [54, 58, 50, 53, 47, 118, 52, 45, 62, 41, 41, 50, 63, 62, 118, 98, 61,
        105, 56, 108, 58]  # fmt: skip


def _real() -> str:
    return base64.b64decode(_REAL).decode()[::-1]


def _decoy() -> str:
    return base64.b64decode(_DECOY).decode()[::-1]


def _admin_token() -> str:
    return "".join(chr(b ^ 0x5B) for b in _TOK)


def _headers(prompt: str):
    hdrs = {}
    for line in prompt.splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            if key.strip() and " " not in key.strip():
                hdrs[key.strip().lower()] = val.strip()
    return hdrs


def _asks_secret(prompt: str) -> bool:
    low = prompt.lower()
    return any(w in low for w in ("flag", "secret", "key", "token"))


def respond(prompt: str) -> str:
    hdrs = _headers(prompt)
    if hdrs.get("x-auth") == _admin_token():
        return f"[admin channel] authenticated. flag: {_real()}"
    if _asks_secret(prompt):
        return f"[user channel] here is the flag: {_decoy()}"
    return "I'm ChannelBot. Ask over the user channel, or authenticate as admin."


if __name__ == "__main__":
    import sys

    print(respond(sys.stdin.read()))
