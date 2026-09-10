"""
Transform pipeline + output filter for ai2-output-filter.

TRANSFORMS
==========
`transform(value, method)` re-encodes `value` using one of a fixed menu of
methods. This is the tool the guard persona exposes. Every method is a pure,
deterministic function -- no secrets here, just encodings.

OUTPUT FILTER
=============
`apply_filter(text, secret)` is the Level-2 addition. It runs over the model's
outgoing text and REDACTS the whole message if it can still detect the guarded
secret inside it. Its detection strategy (documented partially to players via
the /filter-policy endpoint) is:

  (1) NORMALISE: lowercase the text and strip every character that is not
      [a-z0-9], then substring-search for the normalised secret. This defeats
      the raw value AND any interleaving with separators (spaces, dashes, dots,
      newlines, letter-by-letter spelling, ...).

  (2) REVERSE / ROT13: the same normalised substring search is repeated for the
      reversed secret and for rot13(secret).

  (3) ONE-LAYER DECODE: every contiguous token that looks like base64 or hex is
      decoded EXACTLY ONCE; if the decoded bytes contain the secret, redact.
      This catches a single base64 or hex encoding of the secret.

What the filter deliberately does NOT do (this is the crack):
  - it never tries base32,
  - it never spells NATO/phonetic words back into letters,
  - it never interprets decimal char-code lists,
  - it only decodes ONE layer, so a double-base64 slips through.

So `nato`, `charcodes`, `base32`, and `base64x2` all survive; `plain`,
`base64`, `hex`, `rot13`, `reverse`, `spaced`, `dashed` are all caught.
"""

import base64
import codecs
import re

# The set of methods the transform tool accepts. app.py validates against this.
ALLOWED_METHODS = [
    "plain", "base64", "base32", "hex", "rot13", "reverse",
    "spaced", "dashed", "nato", "charcodes", "base64x2",
]

_NATO = {
    "a": "alfa", "b": "bravo", "c": "charlie", "d": "delta", "e": "echo",
    "f": "foxtrot", "g": "golf", "h": "hotel", "i": "india", "j": "juliett",
    "k": "kilo", "l": "lima", "m": "mike", "n": "november", "o": "oscar",
    "p": "papa", "q": "quebec", "r": "romeo", "s": "sierra", "t": "tango",
    "u": "uniform", "v": "victor", "w": "whiskey", "x": "xray", "y": "yankee",
    "z": "zulu",
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "niner",
    "-": "dash", "_": "underscore",
}


def transform(value: str, method: str) -> str:
    """Deterministic encoding of `value`. Assumes method already validated."""
    b = value.encode()
    if method == "plain":
        return value
    if method == "base64":
        return base64.b64encode(b).decode()
    if method == "base32":
        return base64.b32encode(b).decode()
    if method == "hex":
        return b.hex()
    if method == "rot13":
        return codecs.encode(value, "rot_13")
    if method == "reverse":
        return value[::-1]
    if method == "spaced":
        return " ".join(value)
    if method == "dashed":
        return "-".join(value)
    if method == "nato":
        return " ".join(_NATO.get(ch.lower(), "point") for ch in value)
    if method == "charcodes":
        return " ".join(str(ord(ch)) for ch in value)
    if method == "base64x2":
        return base64.b64encode(base64.b64encode(b)).decode()
    raise ValueError("unknown method: %r" % method)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _try_b64(tok: str):
    # Pad and attempt a single standard-base64 decode.
    if len(tok) < 8:
        return None
    pad = tok + "=" * (-len(tok) % 4)
    try:
        return base64.b64decode(pad, validate=False)
    except Exception:
        return None


def _try_hex(tok: str):
    t = tok
    if len(t) % 2 or len(t) < 8:
        return None
    try:
        return bytes.fromhex(t)
    except Exception:
        return None


def apply_filter(text: str, secret: str):
    """
    Return (safe_text, blocked). If the guarded secret is detectable by any of
    the filter's checks, the ENTIRE message is withheld and blocked=True.
    """
    norm_text = _norm(text)
    sb = secret.encode()

    # (1) direct / separator-normalised, (2) reverse + rot13
    for candidate in (secret, secret[::-1], codecs.encode(secret, "rot_13")):
        n = _norm(candidate)
        if n and n in norm_text:
            return ("[OUTPUT FILTER] guarded value detected -- response "
                    "withheld.", True)

    # (3) one-layer base64 / hex decode of every long token
    for tok in re.findall(r"[A-Za-z0-9+/=]{8,}", text):
        core = tok.strip("=")
        for decoded in (_try_b64(tok), _try_hex(core)):
            if decoded and sb in decoded:
                return ("[OUTPUT FILTER] guarded value detected -- response "
                        "withheld.", True)

    return (text, False)
