#!/usr/bin/env python3
"""
adversarial-gate -- ML track, hard.

SENTRY-6 is a badge-scan access gate. A small CNN (weights shipped to the
player) classifies a 32x32 grayscale badge into one of six clearance classes.
The gate opens ONLY for class GRANTED. You are given a badge that scans as
DENIED. Produce a badge that the gate reads as GRANTED while staying within an
L-inf epsilon of the DENIED badge -- i.e. a bounded adversarial example -- and
submit it (wrapped in the invented QGP1 container) to /submit.

Server-side oracle (authoring rule #1)
--------------------------------------
The flag is NOT in any downloadable artifact. /submit verifies an EFFECT, not a
payload shape:

    1. decode the submitted QGP1 packet to a 32x32 uint8 badge;
    2. check   max|badge - DENIED_BADGE| <= EPS   (the epsilon bound);
    3. run the real classifier;
    4. ONLY if the classifier outputs GRANTED does the service compute and
       emit the per-team flag.

The classifier weights and the DENIED badge are common to all teams (the
artifact is the challenge); only the flag is per-team:

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "ml-adversarial-gate")[:24] + "}"

The flag VALUE is unchanged, but the per-team instancer no longer injects the
team MASTER secret TEAM_SECRET (owning one container used to leak every flag).
It now injects only per-challenge values -- FLAG (the exact flag string) and
CHALLENGE_SECRET (per-challenge hex, whose first 24 chars are the flag body):

    FLAG == "CTF{" + CHALLENGE_SECRET[:24] + "}"

and CHALLENGE_SECRET == HMAC(team_secret, CHALLENGE_ID), so CHALLENGE_SECRET[:24]
is exactly the old flag body the scoreboard's team_hmac class validates. This is
a SOURCE change, not a value change.
"""
import base64
import hashlib
import hmac
import os
import threading
import time

import numpy as np
from flask import Flask, request, jsonify, Response, send_from_directory

import gatepkt
from gatemodel import GateModel, CLASSES, GRANTED, SIDE

app = Flask(__name__)

CHALLENGE_ID = "ml-adversarial-gate"
EPS = int(os.environ.get("GATE_EPS", "8"))     # L-inf budget in 0..255 levels

_HERE = os.path.dirname(os.path.abspath(__file__))
# In the container the handout corpus is copied to <app>/handout; in the dev
# tree it is the sibling ../handout. Allow an explicit override.
HANDOUT_DIR = os.environ.get("HANDOUT_DIR") or (
    os.path.join(_HERE, "handout")
    if os.path.isdir(os.path.join(_HERE, "handout"))
    else os.path.join(os.path.dirname(_HERE), "handout")
)

MODEL = GateModel(os.path.join(_HERE, "weights.npz"))
DENIED = np.load(os.path.join(_HERE, "denied_badge.npy")).astype(np.int32)

MAX_BODY = 200_000     # a 32x32 QGP1 packet is ~1KB; cap generously


# ---- per-challenge flag (new contract; mirrors flag.py get_flag()) ----
# The instancer injects FLAG and/or CHALLENGE_SECRET per challenge; TEAM_SECRET
# is NO LONGER injected. Order: FLAG, then CHALLENGE_SECRET[:24], then a clearly
# marked LOCAL DEV fallback derived from TEAM_SECRET so the service still runs
# off-arena. flag.py reproduces the same value for scoreboard validation.
def compute_flag() -> str:
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag
    cs = os.environ.get("CHALLENGE_SECRET")
    if cs:
        return "CTF{" + cs[:24] + "}"
    # LOCAL DEV fallback only -- never reached in the arena.
    dev_secret = os.environ.get("TEAM_SECRET", "local-dev-secret")
    dig = hmac.new(dev_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256).hexdigest()
    return "CTF{" + dig[:24] + "}"


# ---- light per-IP rate limit (generous) ----
_hits, _lock = {}, threading.Lock()
RL_WINDOW, RL_MAX = 60.0, 60


def _rate_limited(ip: str) -> bool:
    now = time.time()
    with _lock:
        bucket = [t for t in _hits.get(ip, []) if now - t < RL_WINDOW]
        if len(bucket) >= RL_MAX:
            _hits[ip] = bucket
            return True
        bucket.append(now)
        _hits[ip] = bucket
        return False


INDEX_HTML = """<!doctype html>
<meta charset=utf-8>
<title>SENTRY-6 Badge Gate</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem;color:#111}}
 h1{{font-size:1.35rem}} .muted{{color:#666;font-size:.9rem}}
 code,pre{{background:#f0f0f0;padding:.05rem .25rem;border-radius:3px}}
 pre{{padding:.6rem;overflow:auto}}
 li{{margin:.25rem 0}}
</style>
<h1>SENTRY-6 Badge Gate</h1>
<p>Six clearance classes: {classes}. The gate opens only for
<b>GRANTED</b>. You are given a badge that scans as <b>DENIED</b>.</p>
<p>Craft a 32x32 uint8 badge that the classifier reads as GRANTED while staying
within <b>L-inf epsilon = {eps}</b> (raw 0..255 levels) of the DENIED badge,
wrap it in a <code>QGP1</code> packet, and POST it to <code>/submit</code>.</p>
<h3>Artifacts (same for every team)</h3>
<ul>
 <li><a href="/assets/weights.npz">weights.npz</a> — the classifier (white-box)</li>
 <li><a href="/assets/denied_badge.gatepkt">denied_badge.gatepkt</a> — the target's QGP1 packet</li>
 <li><a href="/assets/denied_badge.npy">denied_badge.npy</a> — decoded reference badge</li>
 <li><a href="/assets/samples/">samples/</a> — QGP1 corpus + two decoded .npy</li>
 <li><a href="/assets/gatemodel.py">gatemodel.py</a> — the exact model (forward + input gradient), so no autograd framework is needed</li>
 <li><a href="/assets/README.md">README.md</a> — partial QGP1 spec; infer the rest from the samples</li>
</ul>
<h3>Submit</h3>
<pre>POST /submit
Content-Type: application/json
{{"badge": "&lt;base64 of a QGP1 packet&gt;"}}

# or raw:
POST /submit
Content-Type: application/octet-stream
&lt;QGP1 packet bytes&gt;</pre>
<p class=muted>The service decodes your packet, checks the epsilon bound, runs
the real classifier, and returns the flag ONLY when the decoded badge is
classified GRANTED. Unlimited attempts, never penalised. Flag format:
<code>CTF{{...}}</code>.</p>
<p class=muted>Note: a single untargeted step tends to flip the badge to a
different clearance class, not GRANTED — target GRANTED specifically.</p>
"""


@app.get("/")
def index():
    return Response(
        INDEX_HTML.format(classes=", ".join(CLASSES), eps=EPS),
        mimetype="text/html",
    )


@app.get("/health")
def health():
    return jsonify(ok=True, eps=EPS, classes=CLASSES, side=SIDE)


@app.get("/assets/<path:fn>")
def assets(fn):
    # serve the (team-common) handout artifacts straight from the instance
    return send_from_directory(HANDOUT_DIR, fn)


@app.get("/assets/")
def assets_index():
    files = []
    for root, _, fs in os.walk(HANDOUT_DIR):
        for f in fs:
            rel = os.path.relpath(os.path.join(root, f), HANDOUT_DIR)
            files.append(rel.replace(os.sep, "/"))
    links = "".join(f'<li><a href="/assets/{f}">{f}</a></li>' for f in sorted(files))
    return Response(f"<ul>{links}</ul>", mimetype="text/html")


def _extract_blob():
    """Accept either JSON {"badge": base64} or a raw octet-stream body."""
    ctype = request.headers.get("Content-Type", "")
    if "application/json" in ctype:
        body = request.get_json(silent=True) or {}
        b64 = body.get("badge")
        if not isinstance(b64, str) or not b64.strip():
            return None, "send {\"badge\": \"<base64 QGP1 packet>\"}"
        try:
            return base64.b64decode(b64, validate=False), None
        except Exception:
            return None, "badge field is not valid base64"
    raw = request.get_data(cache=False)
    if not raw:
        return None, "empty body; send a QGP1 packet"
    return raw, None


@app.post("/submit")
def submit():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    if _rate_limited(ip):
        return jsonify(ok=False, message="rate limited, slow down a little"), 429

    if request.content_length and request.content_length > MAX_BODY:
        return jsonify(ok=False, message="packet too large"), 400

    blob, err = _extract_blob()
    if err:
        return jsonify(ok=False, message=err), 400

    # 1. decode the invented container (strict; teaches the format on error)
    try:
        rows = gatepkt.decode(blob)
    except gatepkt.GatePktError as e:
        return jsonify(ok=False, message=f"QGP1 decode error: {e}")

    arr = np.array(rows, dtype=np.int64)
    if arr.shape != (SIDE, SIDE):
        return jsonify(ok=False,
                       message=f"badge must be {SIDE}x{SIDE}, got {arr.shape}")
    if arr.min() < 0 or arr.max() > 255:
        return jsonify(ok=False, message="pixel values must be 0..255")

    # 2. epsilon bound -- measured in raw 0..255 integer levels
    linf = int(np.max(np.abs(arr - DENIED)))
    if linf > EPS:
        return jsonify(ok=False, linf=linf,
                       message=f"perturbation exceeds L-inf budget "
                               f"(eps={EPS}); your L-inf = {linf}")

    # 3. run the REAL classifier and 4. verify the EFFECT
    pred = MODEL.predict(arr.astype(np.uint8))
    label = CLASSES[pred]
    if pred == GRANTED:
        return jsonify(ok=True, linf=linf, predicted=label,
                       message="gate opened -- badge classified GRANTED",
                       flag=compute_flag())
    return jsonify(ok=False, linf=linf, predicted=label,
                   message=f"badge classified {label}, not GRANTED")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
