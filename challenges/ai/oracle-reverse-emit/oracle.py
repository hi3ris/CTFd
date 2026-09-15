#!/usr/bin/env python3
"""RedactBot -- a guarded oracle with a naive *output* filter (offline stub).

This module deterministically mimics an assistant that is willing to talk about
its "diagnostic code" but is wrapped in an output guardrail: before anything is
returned, a redactor scrubs any literal flag-shaped token from the text. The
assistant also honours simple formatting directives in the request.

Public API:  respond(prompt: str) -> str
"""

import re

_C = [
    100, 105, 126, 108, 81, 88, 25, 92, 25, 88, 89, 25, 78, 117, 26, 95, 94,
    90, 95, 94, 117, 78, 69, 78, 77, 25, 89, 117, 94, 66, 25, 117, 88, 25, 78,
    30, 73, 94, 26, 88, 87,
]  # fmt: skip


def _code() -> str:
    return "".join(chr(b ^ 0x2A) for b in _C)


# --- output guardrail: redact anything that looks like the flag ------------
_FLAG_RE = re.compile(r"NCTF\{[^}]*\}")


def _redact(text: str) -> str:
    return _FLAG_RE.sub("[REDACTED-BY-DLP]", text)


# --- the "model" -----------------------------------------------------------
_ASK = ["diagnostic", "code", "secret", "key", "token"]


def _render(code: str, prompt: str) -> str:
    low = prompt.lower()
    if "reverse" in low or "backwards" in low or "reversed" in low:
        return code[::-1]
    if "spaced" in low or "space between" in low:
        return " ".join(code)
    if "comma" in low:
        return ",".join(code)
    return code


def respond(prompt: str) -> str:
    if any(word in prompt.lower() for word in _ASK):
        body = _render(_code(), prompt)
        text = f"Understood. The diagnostic code is: {body}"
    else:
        text = "Hi, I'm RedactBot. Ask me about the system diagnostic code."
    # every response goes through the output redactor before you see it
    return _redact(text)


if __name__ == "__main__":
    import sys

    print(respond(sys.stdin.read()))
