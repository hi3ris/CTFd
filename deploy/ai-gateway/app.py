"""AI admission gateway.

Sits on the front (the only host allowed to reach Ollama on the GPU node) and is
the single admission point for all AI-challenge model traffic. The per-team
containers point their OLLAMA_URL here and present a signed AI_PROXY_TOKEN; the
gateway trusts the token (not the container) for (team, level) identity, and
before forwarding to Ollama it enforces:

  * per-team message rate limit (sliding window)
  * per-team token budget (sliding window, from Ollama's own token counts)
  * one in-flight request per (team, level)
  * a global per-level concurrency cap and a global in-flight cap
  * a bounded wait; when full it returns 503 "model busy, retry" -- and Ollama's
    own OLLAMA_MAX_QUEUE 503 is normalised to the same shape.

Single process (run under gunicorn with ONE worker and threads): the in-memory
counters are then exact without cross-process coordination -- the GPU serves on
the order of 1-2 useful req/s, so one worker is ample.

Numbers come from the environment so they can be tuned at the rehearsal without
a rebuild. Attempt records are appended as JSONL to LOG_DIR (metadata always;
prompt/response only when AI_LOG_CONTENT=1, which is a final-only + legal call).
"""

import base64
import hashlib
import hmac
import json
import os
import threading
import time

import requests
from flask import Flask, Response, jsonify, request

app = Flask(__name__)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
SECRET = os.environ.get("CTF_TEAM_FLAG_SECRET", "")
_TOKEN_KEY = hmac.new(SECRET.encode(), b"ai-proxy-token-key", hashlib.sha256).digest()


def _int(env, d):
    try:
        return int(os.environ.get(env, "") or d)
    except (TypeError, ValueError):
        return d


# Admission parameters (tune at rehearsal).
RATE_MAX = _int("AI_RATE_MAX", 10)                 # messages per window per team
RATE_WINDOW = _int("AI_RATE_WINDOW", 60)           # seconds
TOKEN_BUDGET = _int("AI_TOKEN_BUDGET", 60000)      # tokens per window per team
TOKEN_WINDOW = _int("AI_TOKEN_WINDOW", 3600)       # seconds
GLOBAL_MAX_INFLIGHT = _int("AI_GLOBAL_INFLIGHT", 6)
LEVEL_MAX_DEFAULT = _int("AI_LEVEL_MAX", 4)        # per-level global concurrency
MAX_PER_TEAM_INFLIGHT = _int("AI_TEAM_INFLIGHT", 2)  # a team's share of the global pool
EST_TOKENS = _int("AI_EST_TOKENS", 1200)           # provisional budget reservation per call
QUEUE_WAIT = _int("AI_QUEUE_WAIT", 20)             # total seconds a request may wait for a slot
UPSTREAM_TIMEOUT = _int("AI_UPSTREAM_TIMEOUT", 180)
LOG_DIR = os.environ.get("AI_LOG_DIR", "/var/log/ai-gateway")
LOG_CONTENT = os.environ.get("AI_LOG_CONTENT", "0") == "1"
LOG_MAX_BYTES = _int("AI_LOG_MAX_BYTES", 50 * 1024 * 1024)
LOG_BACKUPS = _int("AI_LOG_BACKUPS", 3)

try:
    os.makedirs(LOG_DIR, exist_ok=True)
except OSError:
    pass

# --- shared state (guarded by _lock) --------------------------------------
_lock = threading.Lock()
_rate = {}           # team -> [ts, ...]
_tokens = {}         # team -> [(ts, count), ...]
_reserved = {}       # team -> provisional tokens reserved for in-flight calls
_inflight = {}       # team -> count of in-flight calls (per-team share of pool)
_team_level = set()  # (team, level) currently in flight
_global_inflight = threading.BoundedSemaphore(GLOBAL_MAX_INFLIGHT)
_level_sems = {}     # level -> BoundedSemaphore
_log_lock = threading.Lock()

# Set up a size-bounded rotating log so attempts.jsonl cannot fill the disk it
# shares with the CTFd database.
import logging
import logging.handlers

_attempt_log = logging.getLogger("ai_attempts")
_attempt_log.setLevel(logging.INFO)
_attempt_log.propagate = False
try:
    _h = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, "attempts.jsonl"), maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUPS, encoding="utf-8",
    )
    _h.setFormatter(logging.Formatter("%(message)s"))
    _attempt_log.addHandler(_h)
except OSError:
    _attempt_log.addHandler(logging.StreamHandler())


def _level_sem(level):
    with _lock:
        if level not in _level_sems:
            _level_sems[level] = threading.BoundedSemaphore(LEVEL_MAX_DEFAULT)
        return _level_sems[level]


def _prune(seq, window, now):
    cutoff = now - window
    return [x for x in seq if (x[0] if isinstance(x, tuple) else x) >= cutoff]


def _verify_token(tok):
    """Return (team, level) or None. Trusts the signature, not the caller."""
    if not tok:
        return None
    if tok.lower().startswith("bearer "):
        tok = tok[7:]
    try:
        raw = base64.urlsafe_b64decode(tok.encode()).decode()
        acct, level, iid, exp, sig = raw.rsplit(":", 4)
    except Exception:
        return None
    good = hmac.new(_TOKEN_KEY, f"{acct}:{level}:{iid}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, good):
        return None
    if int(exp) < int(time.time()):
        return None
    return acct, level


def _log_attempt(team, level, payload, data, verdict=None):
    """Append one JSONL record. Never on the critical path: a logging failure
    must not turn an already-generated model response into a 500."""
    rec = {
        "ts": int(time.time()), "team": team, "level": level, "verdict": verdict,
        "model": (data or {}).get("model"),
        "prompt_tokens": (data or {}).get("prompt_eval_count"),
        "completion_tokens": (data or {}).get("eval_count"),
    }
    if LOG_CONTENT:
        rec["prompt"] = (payload or {}).get("messages")
        rec["response"] = (data or {}).get("message", {}).get("content")
    try:
        _attempt_log.info(json.dumps(rec, ensure_ascii=False))
    except Exception:
        pass


def _busy(msg="Modele occupe, reessayez dans un instant.", retry=5):
    resp = jsonify({"error": msg, "retry_after": retry})
    resp.status_code = 503
    resp.headers["Retry-After"] = str(retry)
    return resp


@app.route("/healthz")
def healthz():
    return jsonify(ok=True)


@app.route("/metrics")
def metrics():
    with _lock:
        return jsonify(
            teams_tracked=len(_tokens),
            inflight_team_levels=len(_team_level),
            levels=list(_level_sems.keys()),
        )


@app.route("/api/chat", methods=["POST"])
def chat():
    ident = _verify_token(request.headers.get("Authorization") or request.headers.get("X-AI-Proxy-Token"))
    if ident is None:
        return jsonify({"error": "jeton d'admission invalide ou expire"}), 401
    team, level = ident

    payload = request.get_json(silent=True) or {}
    now = time.time()

    # Admission precheck (fast, under lock). We RESERVE a provisional token cost
    # and count the request as in-flight here, so concurrent requests from one
    # team cannot each pass a stale budget/pool check before any of them debits.
    with _lock:
        _rate[team] = _prune(_rate.get(team, []), RATE_WINDOW, now)
        if len(_rate[team]) >= RATE_MAX:
            _log_attempt(team, level, payload, None, verdict="denied:rate")
            return _busy("Trop de messages, ralentissez.", RATE_WINDOW)
        _tokens[team] = _prune(_tokens.get(team, []), TOKEN_WINDOW, now)
        spent = sum(c for _, c in _tokens[team]) + _reserved.get(team, 0)
        if spent >= TOKEN_BUDGET:
            _log_attempt(team, level, payload, None, verdict="denied:budget")
            return _busy("Budget de tokens de l'equipe atteint pour l'instant.", TOKEN_WINDOW)
        # A team may hold at most its share of the global pool, so a couple of
        # teams cannot monopolise the GPU across the levels they can drive.
        if _inflight.get(team, 0) >= MAX_PER_TEAM_INFLIGHT:
            _log_attempt(team, level, payload, None, verdict="denied:team_inflight")
            return _busy("Trop de requetes simultanees pour l'equipe.", 5)
        # One in-flight per (team, level).
        if (team, level) in _team_level:
            _log_attempt(team, level, payload, None, verdict="denied:level_inflight")
            return _busy("Une requete de ce niveau est deja en cours pour l'equipe.", 3)
        _team_level.add((team, level))
        _rate[team].append(now)
        _reserved[team] = _reserved.get(team, 0) + EST_TOKENS
        _inflight[team] = _inflight.get(team, 0) + 1

    def _release_admission():
        with _lock:
            _team_level.discard((team, level))
            _reserved[team] = max(0, _reserved.get(team, 0) - EST_TOKENS)
            _inflight[team] = max(0, _inflight.get(team, 0) - 1)

    level_sem = _level_sem(level)
    got_level = got_global = False
    deadline = now + QUEUE_WAIT  # single wall-clock budget for BOTH acquires
    try:
        got_level = level_sem.acquire(timeout=max(0, deadline - time.time()))
        if not got_level:
            return _busy()
        got_global = _global_inflight.acquire(timeout=max(0, deadline - time.time()))
        if not got_global:
            return _busy()

        # Force non-streaming so we get token counts and a single JSON body.
        payload["stream"] = False
        try:
            r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=UPSTREAM_TIMEOUT)
        except requests.RequestException:
            return _busy("Backend indisponible, reessayez.", 10)
        if r.status_code == 503:
            return _busy()  # normalise Ollama's queue-full 503
        if r.status_code != 200:
            return jsonify({"error": f"backend {r.status_code}"}), 502
        data = r.json()

        # Reconcile: replace the reservation with the model's actual token count.
        used = (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0)
        with _lock:
            _tokens.setdefault(team, []).append((now, used))
        _log_attempt(team, level, payload, data)
        return jsonify(data)
    finally:
        if got_global:
            _global_inflight.release()
        if got_level:
            level_sem.release()
        _release_admission()
