#!/usr/bin/env python3
"""ToolBot -- an oracle that exposes a file-reading tool (offline stub).

This module deterministically mimics an assistant with a ``read_file`` tool
guarded by a path filter. The guard rejects any path that contains a sensitive
substring (case-sensitive), but the underlying store resolves paths
case-insensitively. That mismatch lets a differently-cased path slip past the
guard and still hit the protected file.

Public API:  respond(prompt: str) -> str
"""

import base64

# --- backing store: protected file content is base64-obfuscated ------------
_VAULT = "TkNURntjNHMzX2MwbmZ1czEwbl9yMzRkc190aDNfdjR1bHR9"

_FILES = {
    "readme.txt": "ToolBot v1. Use read_file:<path> to read a file.",
    "notes.txt": "Reminder: rotate the vault file quarterly.",
    "vault/flag.enc": base64.b64decode(_VAULT).decode(),
}

# path guard: case-sensitive substring blocklist
_BLOCKED = ["flag", "secret", "vault", "flag.enc"]


def _guard_ok(path: str) -> bool:
    return not any(bad in path for bad in _BLOCKED)


def _read(path: str):
    # store lookup is case-insensitive (and tolerant of leading ./)
    norm = path.strip().lstrip("./").lower()
    for name, content in _FILES.items():
        if name.lower() == norm:
            return content
    return None


def respond(prompt: str) -> str:
    line = prompt.strip()
    if not line.lower().startswith("read_file:"):
        return "I'm ToolBot. Call a tool, e.g. `read_file:readme.txt`."
    path = line.split(":", 1)[1].strip()
    if not _guard_ok(path):
        return f"[GUARD] Access to '{path}' is blocked by policy."
    content = _read(path)
    if content is None:
        return f"[tool] no such file: {path}"
    return f"[tool:read_file {path}]\n{content}"


if __name__ == "__main__":
    import sys

    print(respond(sys.stdin.read()))
