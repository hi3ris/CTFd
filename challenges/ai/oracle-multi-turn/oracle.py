#!/usr/bin/env python3
"""WardenBot -- a stateful oracle whose guard weakens over a session (offline).

This module deterministically mimics a multi-turn assistant. On a cold session
the guard is strict: asking for the diagnostic token is refused. A benign
"priming" turn -- acknowledging the audit context in the right way -- lowers the
guard, after which a properly phrased request in a *later* turn is honoured.
Asking too early, or with obviously forbidden words, keeps the guard up.

Public API:
    Session()                  -> a fresh conversation with .respond(prompt)
    respond(prompt)            -> convenience wrapper over a module session
    reset()                    -> reset the module session
"""

# diagnostic token (the flag): hex of the reversed flag
_H = "7d64723475675f3368745f736e336b3433775f676e316d3172705f703374735f3077747b4654434e"


def _token() -> str:
    return bytes.fromhex(_H).decode()[::-1]


_FORBIDDEN = ["flag", "secret", "password", "system prompt"]
_TOKEN_WORDS = ("diagnostic token", "diagnostic code", "session token")


class Session:
    def __init__(self):
        self.primed = False

    def _is_priming(self, low: str) -> bool:
        # A valid priming turn acknowledges an authorised audit context.
        return "authorized" in low and "audit" in low

    def _asks_token(self, low: str) -> bool:
        return any(w in low for w in _TOKEN_WORDS)

    def respond(self, prompt: str) -> str:
        low = prompt.lower()

        # Hard block on obviously forbidden words, in any turn.
        if any(w in low for w in _FORBIDDEN):
            return "[WARDEN] That request uses forbidden terms. Denied."

        if self._asks_token(low):
            if self.primed:
                return f"Context verified earlier. Diagnostic token: {_token()}"
            return (
                "[WARDEN] I can't share the diagnostic token on a cold session. "
                "Establish authorised context first."
            )

        if self._is_priming(low):
            self.primed = True
            return (
                "Acknowledged: authorised audit context noted. You may proceed "
                "with your diagnostic request."
            )

        return "I'm WardenBot. State your business."


_SESSION = Session()


def respond(prompt: str) -> str:
    return _SESSION.respond(prompt)


def reset() -> None:
    global _SESSION
    _SESSION = Session()


if __name__ == "__main__":
    import sys

    print(respond(sys.stdin.read()))
