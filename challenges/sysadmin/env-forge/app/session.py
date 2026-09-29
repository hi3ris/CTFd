"""Session minting / validation for the Kekeli internal API (excerpt).

HS256 JWTs are signed with os.environ["APP_JWT_SECRET"]. The admin flag is
derived from the same secret, so leaking the secret is game over.
"""

import base64
import hashlib
import hmac
import json
import os

SECRET = os.environ["APP_JWT_SECRET"].encode()
ISS = os.environ.get("APP_JWT_ISS", "kekeli-internal")


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def sign(claims: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    seg = _b64u(json.dumps(header, separators=(",", ":")).encode())
    seg += "." + _b64u(json.dumps(claims, separators=(",", ":")).encode())
    mac = hmac.new(SECRET, seg.encode(), hashlib.sha256).digest()
    return seg + "." + _b64u(mac)


def verify(token: str) -> dict:
    seg, _, sig = token.rpartition(".")
    want = _b64u(hmac.new(SECRET, seg.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(want, sig):
        raise ValueError("bad signature")
    _, _, body = seg.partition(".")
    pad = "=" * (-len(body) % 4)
    return json.loads(base64.urlsafe_b64decode(body + pad))


def admin_flag() -> str:
    body = hmac.new(SECRET, b"nctf:admin-flag:v1", hashlib.sha256).hexdigest()[:12]
    return "NCTF{hs256_secret_leak_forged_" + body + "}"


def handle_admin_flag(token: str) -> str:
    claims = verify(token)
    if claims.get("iss") != ISS or claims.get("role") != "admin":
        raise PermissionError("admin only")
    return admin_flag()
