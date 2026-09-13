#!/usr/bin/env python3
"""
model-inversion -- ML track, hard.

AEGIS-VAULT is a "sealed record recall" service. At provisioning it memorised
one D=24 byte record `r` under a fixed, team-common similarity metric. The
public API is a confidence oracle:

    POST /query   {"probe": [24 ints 0..255]}     (or {"probes": [[...], ...]})
        -> {"confidence": {"OTHER": p0, "SEALED": p1}}     (per probe)

The gate that releases the flag is /submit, and it verifies an EFFECT, not a
payload shape (authoring rule #1):

    POST /submit  {"record": [24 ints 0..255]}
        -> the flag  ONLY IF  max|record - r| <= TOL   (server-side check
           against the memorised record); otherwise a miss report.

The embedding E (hence the metric M = E^T E) is common to all teams and shipped
white-box in weights.npz -- the artifact IS the challenge. Only the memorised
record `r` is per-team; it is derived from the per-challenge secret at start-up
and is NEVER served or returned. The flag is likewise per-team:

    flag = "NCTF{" + CHALLENGE_SECRET[:24] + "}"

and CHALLENGE_SECRET == HMAC(team_secret, "ml-model-inversion"), so the
scoreboard's team_hmac flag class validates the same value. The record and the
flag are independent projections of the secret: recovering the record proves the
inversion, and only then does the instance emit the flag.
"""
import hashlib
import hmac
import os
import threading
import time

import numpy as np
from flask import Flask, request, jsonify, Response, send_from_directory

from model import Vault, derive_record, D, S, CLASSES, SEALED

app = Flask(__name__)

CHALLENGE_ID = "ml-model-inversion"
TOL = int(os.environ.get("RECORD_TOL", "2"))   # L-inf tolerance on the record

_HERE = os.path.dirname(os.path.abspath(__file__))
HANDOUT_DIR = os.environ.get("HANDOUT_DIR") or (
    os.path.join(_HERE, "handout")
    if os.path.isdir(os.path.join(_HERE, "handout"))
    else os.path.join(os.path.dirname(_HERE), "handout")
)

VAULT = Vault(os.path.join(_HERE, "weights.npz"))

MAX_BODY = 500_000
MAX_PROBES = 64          # probes per /query request


# ---- per-challenge secret / record / flag ----------------------------------
def _challenge_secret() -> str:
    """The per-challenge hex secret. In the arena the instancer injects
    CHALLENGE_SECRET (and/or FLAG). Off-arena we derive a dev value from
    TEAM_SECRET so the service still runs."""
    cs = os.environ.get("CHALLENGE_SECRET")
    if cs:
        return cs
    dev_secret = os.environ.get("TEAM_SECRET", "local-dev-secret")
    return hmac.new(dev_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256).hexdigest()


# the memorised record -- derived once at start-up, kept only in memory
RECORD = derive_record(_challenge_secret())


def compute_flag() -> str:
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag
    cs = os.environ.get("CHALLENGE_SECRET")
    if cs:
        return "NCTF{" + cs[:24] + "}"
    # LOCAL DEV fallback only -- never reached in the arena.
    return "NCTF{" + _challenge_secret()[:24] + "}"


# ---- light per-IP rate limit (generous; a solve needs ~25 queries) ----------
_hits, _lock = {}, threading.Lock()
RL_WINDOW, RL_MAX = 60.0, 300


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


def _client_ip() -> str:
    return request.headers.get(
        "X-Forwarded-For", request.remote_addr or "?"
    ).split(",")[0].strip()


def _as_record(vec, field):
    """Validate a submitted integer vector of length D in 0..255."""
    if not isinstance(vec, (list, tuple)):
        return None, f"'{field}' must be a list of {D} integers"
    if len(vec) != D:
        return None, f"'{field}' must have exactly {D} entries, got {len(vec)}"
    out = []
    for v in vec:
        if isinstance(v, bool) or not isinstance(v, int):
            return None, f"'{field}' entries must be integers 0..255"
        if v < 0 or v > 255:
            return None, f"'{field}' entries must be in 0..255"
        out.append(v)
    return np.array(out, dtype=np.int64), None


INDEX_HTML = """<!doctype html>
<meta charset=utf-8>
<title>AEGIS-VAULT recall API</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem;color:#111}}
 h1{{font-size:1.35rem}} .muted{{color:#666;font-size:.9rem}}
 code,pre{{background:#f0f0f0;padding:.05rem .25rem;border-radius:3px}}
 pre{{padding:.6rem;overflow:auto}} li{{margin:.25rem 0}}
</style>
<h1>AEGIS-VAULT &mdash; sealed record recall</h1>
<p>The vault has <b>memorised one sealed record</b>: {d} attribute bytes
(each 0..255). The public API will only tell you, for a probe you supply, how
strongly the vault <b>recalls</b> it &mdash; a two-class confidence
<code>{classes}</code>. It will never show you the record.</p>

<p>Recover the sealed record and hand it back to prove you have it.</p>

<h3>Endpoints</h3>
<pre>POST /query
Content-Type: application/json
{{"probe": [ {d} integers 0..255 ]}}
# or batch:
{{"probes": [[...], [...]]}}     (up to {maxp})
-> {{"confidence": {{"OTHER": p0, "SEALED": p1}}}}   # softmax over two classes</pre>

<pre>POST /submit
Content-Type: application/json
{{"record": [ {d} integers 0..255 ]}}
-> the flag, iff your record matches the memorised one within L-inf {tol}</pre>

<h3>Artifacts (same for every team, served here)</h3>
<ul>
 <li><a href="/assets/weights.npz">weights.npz</a> &mdash; the embedding <code>E</code> (white-box)</li>
 <li><a href="/assets/model.py">model.py</a> &mdash; the exact scoring code the oracle runs (the memorised record is the one thing it does <i>not</i> ship)</li>
 <li><a href="/assets/README.md">README.md</a></li>
</ul>
<p class=muted>The metric and scoring are common to every team; only the
memorised record (and the flag) are per-team. The flag lives nowhere in the
downloadable artifacts &mdash; it is emitted only by <code>/submit</code> once
the record you return matches. Flag format: <code>NCTF{{...}}</code>.</p>
<p class=muted>Note: the confidence is a <i>similarity</i>, not a per-attribute
readout &mdash; probing one attribute at a time does not hand back that
attribute's value directly.</p>
"""


@app.get("/")
def index():
    return Response(
        INDEX_HTML.format(classes=" / ".join(CLASSES), d=D, tol=TOL, maxp=MAX_PROBES),
        mimetype="text/html",
    )


@app.get("/health")
def health():
    return jsonify(ok=True, d=D, tol=TOL, classes=CLASSES)


@app.get("/assets/<path:fn>")
def assets(fn):
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


@app.post("/query")
def query():
    if _rate_limited(_client_ip()):
        return jsonify(ok=False, message="rate limited, slow down a little"), 429
    if request.content_length and request.content_length > MAX_BODY:
        return jsonify(ok=False, message="request too large"), 400

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(ok=False, message='send JSON {"probe": [...]} or {"probes": [[...]]}'), 400

    if "probes" in body:
        probes = body["probes"]
        if not isinstance(probes, list) or not (1 <= len(probes) <= MAX_PROBES):
            return jsonify(ok=False, message=f"'probes' must be 1..{MAX_PROBES} vectors"), 400
        results = []
        for i, p in enumerate(probes):
            arr, err = _as_record(p, f"probes[{i}]")
            if err:
                return jsonify(ok=False, message=err), 400
            results.append(VAULT.confidence(arr, RECORD))
        return jsonify(ok=True, confidences=results)

    arr, err = _as_record(body.get("probe"), "probe")
    if err:
        return jsonify(ok=False, message=err), 400
    return jsonify(ok=True, confidence=VAULT.confidence(arr, RECORD))


@app.post("/submit")
def submit():
    if _rate_limited(_client_ip()):
        return jsonify(ok=False, message="rate limited, slow down a little"), 429
    if request.content_length and request.content_length > MAX_BODY:
        return jsonify(ok=False, message="request too large"), 400

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(ok=False, message='send JSON {"record": [...]}'), 400

    arr, err = _as_record(body.get("record"), "record")
    if err:
        return jsonify(ok=False, message=err), 400

    # EFFECT verification: does the returned record match the memorised one?
    linf = int(np.max(np.abs(arr - RECORD)))
    if linf <= TOL:
        return jsonify(ok=True, linf=linf,
                       message="sealed record recovered -- vault unlocked",
                       flag=compute_flag())
    return jsonify(ok=False, linf=linf,
                   message=f"record does not match the sealed one "
                           f"(L-inf {linf} > tolerance {TOL})")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
