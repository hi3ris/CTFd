#!/usr/bin/env python3
"""
jwt-cousin -- a login service that uses a homemade, JWT-*like* token.

It is deliberately NOT a JWT:
  * there is no `header` segment; a token is  <payload>.<sig>  (two parts)
  * the signature is NOT HMAC over `base64(header).base64(payload)`.
    It is a truncated HMAC over a *canonical claim string* that the server
    rebuilds from a fixed, reordered SUBSET of the claims.

Anything that reaches for a stock JWT library / jwt.io will fail to parse
or fail to verify. The flaw is in what the canonical string does (and does
not) cover -- see the writeup.

Nothing in this file is a downloadable artifact for players: the running
service is the oracle. The flag is emitted only after an admin-only *effect*
is actually performed on the server.
"""
import base64
import hashlib
import hmac
import json
import os
import threading
import time

from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Secrets. Injected by the platform at container creation time and NEVER
# present in any file a player can download.
# ---------------------------------------------------------------------------
# The key used to sign tokens. Random per instance; brute forcing it is not
# the intended path (and is not feasible), and it never touches the flag.
SIGNING_KEY = os.environ.get("SIGNING_KEY", "demo-instance-signing-key").encode()

CHALLENGE_ID = "web-jwt-cousin"


def get_flag() -> str:
    """This instance's flag, under the per-challenge injection contract.

    The instancier no longer injects the team master secret. It injects
    per-challenge values instead:
      1. FLAG              -- the exact flag string, used verbatim;
      2. CHALLENGE_SECRET  -- per-challenge hex; flag == "NCTF{"+hex[:24]+"}".
    Off-arena (dev), where neither is set, fall back to deriving from
    TEAM_SECRET so `docker compose up` still works. The flag VALUE is
    unchanged: CHALLENGE_SECRET == HMAC_SHA256(team_secret, CHALLENGE_ID),
    so CHALLENGE_SECRET[:24] is exactly the historical flag body.
    """
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag
    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "NCTF{" + challenge_secret[:24] + "}"
    # LOCAL DEV ONLY -- no per-challenge secret present in the environment.
    team_secret = os.environ.get("TEAM_SECRET", "local-dev-secret")
    digest = hmac.new(team_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256).hexdigest()
    return "NCTF{" + digest[:24] + "}"


# ---------------------------------------------------------------------------
# Token codec.
# ---------------------------------------------------------------------------
def b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64u_dec(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def canonical(claims: dict) -> str:
    """
    The claim string that actually gets signed.

    Note the three deliberate non-JWT choices:
      1. it is built from a FIXED, reordered subset of claims (sub, exp, v);
      2. the `role` and `alg` claims are NOT part of it;
      3. delimiter is ';' and pairs are key=value, nothing base64 about it.
    """
    return "sub=%s;exp=%d;v=%d" % (claims["sub"], int(claims["exp"]), int(claims["v"]))


def sign(claims: dict) -> str:
    mac = hmac.new(SIGNING_KEY, canonical(claims).encode(), hashlib.sha256).hexdigest()
    return mac[:32]  # truncated -- another small non-standard touch


def issue(sub: str, role: str) -> str:
    claims = {
        "sub": sub,
        "role": role,
        "exp": int(time.time()) + 3600,
        "v": 1,
        "alg": "HS256",  # decoy: present but IGNORED on verify
    }
    payload = b64u(json.dumps(claims, separators=(",", ":")).encode())
    return payload + "." + sign(claims)


def verify(token: str):
    try:
        payload_b64, sig = token.split(".")
        claims = json.loads(b64u_dec(payload_b64))
        # required claims for the canonical string must be present & typed
        _ = str(claims["sub"])
        _ = int(claims["exp"])
        _ = int(claims["v"])
    except Exception:
        return None
    # `alg` is intentionally ignored -- no algorithm confusion here.
    expected = sign(claims)
    if not hmac.compare_digest(expected, str(sig)):
        return None
    if int(claims["exp"]) < int(time.time()):
        return None
    return claims


def bearer():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    # also accept a `token` form field / json field for convenience
    if request.is_json and isinstance(request.json, dict):
        return request.json.get("token")
    return request.form.get("token") or request.args.get("token")


# ---------------------------------------------------------------------------
# Public accounts. These are meant to be handed to players; the interesting
# role ("admin") has no public password.
# ---------------------------------------------------------------------------
ACCOUNTS = {
    "guest": {"password": "guest", "role": "guest"},
    "staff": {"password": "staff", "role": "staff"},
    # "root" account exists but you don't get its password.
}

# server-side state the admin action mutates -- this is the *effect*.
STATE = {"maintenance": True, "rotations": 0}
STATE_LOCK = threading.Lock()


INDEX = """<!doctype html><meta charset=utf-8>
<title>Cousin SSO</title>
<style>body{font-family:system-ui,sans-serif;max-width:52rem;margin:3rem auto;padding:0 1rem;line-height:1.5}
code,pre{background:#f4f4f4;padding:.1rem .3rem;border-radius:4px}pre{padding:1rem;overflow:auto}</style>
<h1>Cousin SSO</h1>
<p>Internal single-sign-on for the operations console. Tokens are our own
format &mdash; <em>not</em> JWT, so don't bother with the usual libraries.</p>

<h2>Roles</h2>
<ul><li><code>guest</code> &mdash; read-only</li>
<li><code>staff</code> &mdash; can view reports</li>
<li><code>admin</code> &mdash; can rotate the console (maintenance ops)</li></ul>

<h2>Public demo accounts</h2>
<ul><li><code>guest</code> / <code>guest</code></li>
<li><code>staff</code> / <code>staff</code></li></ul>

<h2>API</h2>
<pre>POST /api/login      {"user":"guest","pass":"guest"}      -&gt; {"token": "..."}
GET  /api/whoami     Authorization: Bearer &lt;token&gt;         -&gt; your claims
POST /api/admin/rotate  Authorization: Bearer &lt;token&gt;      -&gt; admin only</pre>

<p>Only an <code>admin</code> may rotate the console. Do that and the console
hands back the operations flag. Flag format: <code>NCTF{...}</code>.</p>
"""


@app.get("/")
def index():
    return Response(INDEX, mimetype="text/html")


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or request.form
    user = (data.get("user") or "").strip()
    pw = data.get("pass") or ""
    acct = ACCOUNTS.get(user)
    if not acct or acct["password"] != pw:
        return jsonify(error="invalid credentials"), 401
    return jsonify(token=issue(user, acct["role"]))


@app.get("/api/whoami")
def whoami():
    claims = verify(bearer() or "")
    if not claims:
        return jsonify(error="invalid or expired token"), 401
    return jsonify(sub=claims.get("sub"), role=claims.get("role"), exp=claims.get("exp"))


@app.route("/api/admin/rotate", methods=["POST", "GET"])
def rotate():
    claims = verify(bearer() or "")
    if not claims:
        return jsonify(error="invalid or expired token"), 401

    # Authorization decision is made on `role` -- which the signature does
    # NOT cover. We verify the *effect* (an admin-only rotation happened),
    # not the shape of whatever token got us here.
    if claims.get("role") != "admin":
        return jsonify(error="forbidden: admin role required",
                       your_role=claims.get("role")), 403

    with STATE_LOCK:
        STATE["maintenance"] = False
        STATE["rotations"] += 1
        n = STATE["rotations"]

    return jsonify(
        ok=True,
        message="console rotated; maintenance mode cleared",
        rotations=n,
        flag=get_flag(),
    )


@app.get("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
