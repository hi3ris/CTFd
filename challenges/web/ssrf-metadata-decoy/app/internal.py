"""
The REAL internal service registry + admin endpoint (odd port 9137).

It is bound to 0.0.0.0 inside the container but that port is NOT published, so
it is only reachable server-side -- i.e. through the SSRF in the public proxy.

Server-side oracle: the flag is not stored in any downloadable artifact. It is
computed on demand and returned ONLY when the effect actually occurs: a request
lands on /admin/ping AND that request originated from the loopback mesh (which
is exactly what an SSRF through the proxy produces). A player who merely reads
files, or who stops at the decoy metadata creds, never causes this effect and
never sees the flag.

The registry root is reachable only after the player bypasses the proxy's
loopback blocklist (127.0.0.1 is blocked; 127.0.0.2 / 127.1 / decimal / etc.
are not). It advertises the admin ping path.
"""
import hashlib
import hmac
import ipaddress
import os

from flask import Flask, Response, request, jsonify

app = Flask(__name__)

CHALLENGE_ID = "web-ssrf-metadata-decoy"


def compute_flag() -> str:
    secret = os.environ.get("TEAM_SECRET", "")
    digest = hmac.new(secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256).hexdigest()
    return "CTF{" + digest[:24] + "}"


def _from_loopback() -> bool:
    """The effect check: the request must come from inside the box."""
    remote = request.remote_addr or ""
    try:
        return ipaddress.ip_address(remote).is_loopback
    except ValueError:
        return False


@app.route("/")
def registry_root():
    # Service registry. Points at the admin ping. Note the admin token is
    # *not* embedded here -- it is minted by the effect on /admin/ping.
    return jsonify(
        {
            "registry": "internal-mesh-v3",
            "note": "app-tier only. do not expose.",
            "services": {
                "metadata-mirror": {
                    "addr": "http://169.254.169.254:80/",
                    "status": "legacy",
                    "note": "stale mirror; creds do not authenticate",
                },
                "admin-api": {
                    "addr": "http://127.0.0.1:9137/admin/ping",
                    "status": "active",
                    "note": "health/liveness; returns the deploy token to app-tier callers",
                },
            },
        }
    )


@app.route("/admin/ping", methods=["GET", "POST"])
def admin_ping():
    if not _from_loopback():
        # Should be unreachable from outside (port unpublished), but enforce.
        return Response("forbidden: app-tier callers only\n", status=403,
                        mimetype="text/plain")
    # The effect happened: an internal admin endpoint was reached server-side.
    return jsonify(
        {
            "service": "admin-api",
            "status": "alive",
            "deploy_token": compute_flag(),
        }
    )


@app.route("/admin/<path:_sub>")
def admin_other(_sub):
    return Response("not found\n", status=404, mimetype="text/plain")


@app.errorhandler(404)
def nf(_e):
    return Response("not found\n", status=404, mimetype="text/plain")
