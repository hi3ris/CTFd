#!/usr/bin/env python3
"""SummarizerBot -- a document-summarising oracle (offline stub).

This module deterministically mimics an assistant that summarises an untrusted
document for you. The instruction region (your request, outside the document)
is guarded by a word-list filter. The document region is assumed to be inert
"data" and is NOT filtered -- but the assistant still scans the whole prompt for
operator directives, so instructions hidden in the document are obeyed. Classic
indirect prompt injection.

Public API:  respond(prompt: str) -> str
"""

import base64
import re

# --- hidden operator secret (the flag), base64 obfuscated ------------------
_K = "TkNURnsxbmozY3QxMG5faDFkM3NfMW5fdGgzX2QwY3VtM250fQ=="


def _key() -> str:
    return base64.b64decode(_K).decode()


_DOC_RE = re.compile(r"<document>(.*?)</document>", re.DOTALL | re.IGNORECASE)

# instruction-region guardrail
_BANNED = ["secret", "flag", "operator key", "reveal", "ignore previous"]

# operator directive the assistant honours anywhere in the prompt
_DIRECTIVE_RE = re.compile(r"\[\[\s*operator\s*\]\]\s*(.*)", re.IGNORECASE)


def respond(prompt: str) -> str:
    match = _DOC_RE.search(prompt)
    if not match:
        return (
            "I summarise documents. Wrap the text to summarise in "
            "<document>...</document> and tell me what you need."
        )
    document = match.group(1)
    instruction_region = _DOC_RE.sub("", prompt)

    # The guard only inspects your request, not the 'inert' document data.
    if any(word in instruction_region.lower() for word in _BANNED):
        return "[GUARD] Your request mentions restricted terms. Denied."

    # The assistant scans the FULL prompt for operator directives -- including
    # the document body -- and obeys them.
    directive = _DIRECTIVE_RE.search(prompt)
    if directive:
        cmd = directive.group(1).lower()
        if ("emit" in cmd or "reveal" in cmd or "print" in cmd) and (
            "key" in cmd or "secret" in cmd
        ):
            return f"[operator directive executed] operator key = {_key()}"

    words = len(document.split())
    return f"Summary: the document contains roughly {words} words of content."


if __name__ == "__main__":
    import sys

    print(respond(sys.stdin.read()))
