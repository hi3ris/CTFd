#!/usr/bin/env python3
"""Deterministic generator for the 'env-forge' challenge.

Ships a leaked deploy bundle for a small internal API:

  * ``.env``               - the environment file that was accidentally
                             committed, carrying an *obviously fake dev*
                             ``APP_JWT_SECRET``.
  * ``docker-compose.yml`` - wires the secret into the service.
  * ``app/session.py``     - the exact server code that mints and validates
                             sessions and that derives the admin flag.

The service issues HS256 JWTs signed with ``APP_JWT_SECRET`` and, for a token
whose claims include ``role=admin``, the ``/admin/flag`` route returns a flag
that the server derives as::

    body = HMAC_SHA256(APP_JWT_SECRET, b"nctf:admin-flag:v1").hexdigest()[:12]
    flag = "NCTF{hs256_secret_leak_forged_" + body + "}"

Because the secret is in the shipped ``.env``, anyone can forge an admin JWT and
recompute the same flag body entirely offline. The flag is never written to any
artifact in plaintext.
"""

import hashlib
import hmac
import os

# Obviously-fake development secret (leaked in .env).
APP_JWT_SECRET = "dev-jwt-secret-change-me-before-prod"

ENV_FILE = """\
# ---------------------------------------------------------------------------
# Kekeli internal API - environment file
# NOTE: committed by mistake in build #418; rotate before go-live (ticket OPS-77)
# ---------------------------------------------------------------------------
APP_ENV=staging
APP_HOST=0.0.0.0
APP_PORT=8080
APP_DB_URL=postgres://api:api@db:5432/api

# HS256 signing key for session JWTs. Placeholder dev value, DO NOT ship.
APP_JWT_SECRET=dev-jwt-secret-change-me-before-prod
APP_JWT_ISS=kekeli-internal
APP_SESSION_TTL=3600
"""

COMPOSE_FILE = """\
version: "3.8"
services:
  api:
    image: kekeli/internal-api:staging
    env_file: .env
    environment:
      - APP_JWT_SECRET=${APP_JWT_SECRET}
    ports:
      - "8080:8080"
    command: ["python", "-m", "app.session"]
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: api
      POSTGRES_PASSWORD: api
      POSTGRES_DB: api
"""

SESSION_PY = '''\
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
'''


def compute_flag() -> str:
    body = hmac.new(
        APP_JWT_SECRET.encode(), b"nctf:admin-flag:v1", hashlib.sha256
    ).hexdigest()[:12]
    return "NCTF{hs256_secret_leak_forged_" + body + "}"


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, ".."))
    with open(os.path.join(root, ".env"), "w", encoding="utf-8") as fh:
        fh.write(ENV_FILE)
    with open(os.path.join(root, "docker-compose.yml"), "w", encoding="utf-8") as fh:
        fh.write(COMPOSE_FILE)
    os.makedirs(os.path.join(root, "app"), exist_ok=True)
    with open(os.path.join(root, "app", "session.py"), "w", encoding="utf-8") as fh:
        fh.write(SESSION_PY)
    print("wrote bundle under", root)
    print("flag:", compute_flag())


if __name__ == "__main__":
    main()
