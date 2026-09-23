#!/usr/bin/env python3
"""Backup IMDS — an SSRF that reaches the instance metadata service.

Design (served challenge, per-team flag):

  * ``/fetch?url=X`` is a "backup manifest fetcher". It is meant to read public
    manifests from the backups host, but it does **not block the link-local
    metadata address** ``169.254.169.254`` — the classic SSRF-to-IMDS flaw.
  * Fetching the IMDS credentials path returns this instance's role credentials
    (an ``AccessKeyId`` / ``Token``), modelling ``assume-role``.
  * ``/objects/<key>`` returns a private object only to a request bearing that
    role ``Token``. The flag object is private.

Intended path: `GET /fetch?url=http://169.254.169.254/latest/meta-data/iam/
security-credentials/backup-role` → read the `Token` → `GET /objects/flag` with
`X-Role-Token: <Token>`.

Self-contained: ``/fetch`` only ever answers the metadata address or the
allowlisted backups host from in-process data — it makes no real outbound
request. The flag at ``/flag.txt`` is returned by no route without the role token.
"""
import os
import secrets
import urllib.parse

from flask import Flask, jsonify, request

app = Flask(__name__)

# This instance's role credential (would come from the real IMDS / STS).
_ROLE_TOKEN = "FwoGZXIvYXdz" + secrets.token_urlsafe(24)
IMDS_HOST = "169.254.169.254"
IMDS_CRED_PATH = "/latest/meta-data/iam/security-credentials/backup-role"
BACKUPS_HOST = "backups.nctf.internal"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "gateway-imds",
            "fetch": "/fetch?url=...  (reads backup manifests)",
            "objects": "/objects/<key>  (X-Role-Token required for private keys)",
            "backups_host": BACKUPS_HOST,
        }
    )


@app.route("/fetch")
def fetch():
    raw = request.args.get("url", "")
    u = urllib.parse.urlparse(raw)
    host = u.hostname or ""
    # BUG: link-local metadata address is not blocked.
    if host == IMDS_HOST:
        if u.path == IMDS_CRED_PATH:
            return jsonify(
                {
                    "Code": "Success",
                    "Type": "AWS-HMAC",
                    "AccessKeyId": "ASIA" + "NCTFBACKUPROLE",
                    "Token": _ROLE_TOKEN,
                    "note": "role backup-role may read private backup objects",
                }
            )
        return jsonify({"paths": [IMDS_CRED_PATH]})
    if host == BACKUPS_HOST:
        return jsonify(
            {
                "manifest": "nightly-backup",
                "objects": ["readme", "flag (private)"],
                "hint": "private objects need the backup role credential",
            }
        )
    return jsonify({"error": "host not allowed"}), 400


@app.route("/objects/<key>")
def objects(key):
    if key == "readme":
        return jsonify({"readme": "backups live behind the backup-role."})
    token = request.headers.get("X-Role-Token", "")
    if not secrets.compare_digest(token, _ROLE_TOKEN):
        return jsonify({"error": "private object: role token required"}), 403
    if key == "flag":
        try:
            with open("/flag.txt", encoding="utf-8") as fh:
                return jsonify({"flag": fh.read().strip()})
        except OSError:
            return jsonify({"error": "flag unavailable"}), 500
    return jsonify({"error": "no such object"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
