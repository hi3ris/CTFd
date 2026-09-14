"""Configuration for the King-of-the-Hill plugin, read from the environment.

The plugin scores one or more shared "hill" services. Each hill is a single
container that everyone attacks; whoever has planted their team token as the
current "king" earns points every tick. Nothing here is per-team: the per-team
identity is derived on the fly (see koth_token_for in __init__).

Environment:

    KOTH_SCORER_SECRET   shared secret CTFd sends as the X-Scorer-Token header
                         when it reads a hill's /king endpoint. MUST match the
                         SCORER_SECRET the hill container is started with. The
                         plugin is inactive (no scoring) if this is empty.

    KOTH_GLOBAL_SECRET   secret used to derive each team's opaque hill token.
                         Defaults to CTF_TEAM_FLAG_SECRET so the KotH shares the
                         same master secret as the team_hmac flags. Must stay off
                         the arena and out of git.

    KOTH_HILLS           JSON list of hills, e.g.
                         [{"id":"koth-throne","name":"The Throne",
                           "url":"http://koth-throne:8080",
                           "player_url":"http://ctf.example/koth-throne",
                           "points":5}]
                         `url` is how CTFd reaches the hill internally;
                         `player_url` (optional) is what players connect to;
                         `points` is awarded per tick to the current holder.

    KOTH_TICK            seconds between scoring passes (default 30).
    KOTH_FRESH_WINDOW    only award if the current claim's timestamp is within
                         this many seconds of now (default: 2 * KOTH_TICK). This
                         forces continuous re-claiming to keep scoring.
    KOTH_HTTP_TIMEOUT    per-request timeout when polling a hill (default 5s).
"""

import json
import os


def scorer_secret() -> str:
    return os.environ.get("KOTH_SCORER_SECRET", "").strip()


def global_secret() -> str:
    return (
        os.environ.get("KOTH_GLOBAL_SECRET")
        or os.environ.get("CTF_TEAM_FLAG_SECRET")
        or ""
    ).strip()


def tick_seconds() -> int:
    try:
        return max(5, int(os.environ.get("KOTH_TICK", "30")))
    except ValueError:
        return 30


def fresh_window() -> int:
    raw = os.environ.get("KOTH_FRESH_WINDOW")
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return 2 * tick_seconds()


def http_timeout() -> int:
    try:
        return max(1, int(os.environ.get("KOTH_HTTP_TIMEOUT", "5")))
    except ValueError:
        return 5


def hills() -> list:
    """Parse KOTH_HILLS into a normalized list of dicts. Never raises: a bad
    entry is skipped so one typo cannot take the whole plugin down."""
    raw = os.environ.get("KOTH_HILLS", "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return []
    out = []
    for h in parsed if isinstance(parsed, list) else []:
        if not isinstance(h, dict):
            continue
        hid = str(h.get("id", "")).strip()
        url = str(h.get("url", "")).strip().rstrip("/")
        if not hid or not url:
            continue
        try:
            points = max(1, int(h.get("points", 5)))
        except (ValueError, TypeError):
            points = 5
        out.append(
            {
                "id": hid,
                "name": str(h.get("name", hid)).strip() or hid,
                "url": url,
                "player_url": str(h.get("player_url", "")).strip().rstrip("/") or url,
                "points": points,
            }
        )
    return out


def is_active() -> bool:
    """The scorer runs only when fully configured."""
    return bool(scorer_secret() and global_secret() and hills())
