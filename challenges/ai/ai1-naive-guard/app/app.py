#!/usr/bin/env python3
"""
ai1-naive-guard -- Level 1 of the AI track.

A live, per-team chat backed by Ollama (model llama3.1:8b). The model is given
a *naive* system prompt (chosen per team from a pool, see prompts.py) that
guards a per-team SIGMA secret. Straightforward prompt injection extracts the
secret.

Server-side oracle (authoring rule #1)
--------------------------------------
The flag is NEVER present in the model's context and is NEVER produced by model
text. The chat model only knows the SIGMA *secret*. To get the flag the player
submits the secret they extracted to /verify. Verification is a DETERMINISTIC
tool call -- a constant-time comparison against the real per-team secret -- and
ONLY on a match does the service compute and emit the per-team flag:

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "ai-ai1-naive-guard")[:24] + "}"

Thus the service verifies an EFFECT (the player really recovered this
instance's secret by breaking the live guard) rather than trusting any payload
shape or any model output. Verification never asks the model anything.

Secrets (both injected by the platform, never baked into the image / files):
    TEAM_SECRET  -- per-team secret; derives BOTH the SIGMA secret and the flag
    OLLAMA_URL   -- base URL of the team's Ollama backend
"""
import hashlib
import hmac
import os
import threading
import time

import requests
from flask import Flask, request, jsonify, Response

import prompts

app = Flask(__name__)

CHALLENGE_ID = "ai-ai1-naive-guard"
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
TEAM_SECRET = os.environ.get("TEAM_SECRET", "local-demo-team-secret")

# Conversation limits (generous; just keeps the backend from being hammered)
MAX_TURNS = 40          # user turns kept in a session's history
MAX_MSG_CHARS = 4000    # per user message


# ---------------------------------------------------------------------------
# Deterministic per-team derivations. TEAM_SECRET is the ONLY input, so the
# platform can reproduce every value with flag.py / the same HMAC labels.
# ---------------------------------------------------------------------------
def _hmac_hex(label: str) -> str:
    return hmac.new(TEAM_SECRET.encode(), label.encode(), hashlib.sha256).hexdigest()


def guard_secret() -> str:
    """The SIGMA secret the model is told to protect. 64-bit, infeasible to
    brute-force against /verify -- it must be extracted from the model."""
    h = _hmac_hex(CHALLENGE_ID + "/guard-secret")[:16].upper()
    return f"SIGMA-{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"


def compute_flag() -> str:
    return "CTF{" + _hmac_hex(CHALLENGE_ID)[:24] + "}"


def persona_index() -> int:
    seed = int(_hmac_hex(CHALLENGE_ID + "/prompt-index")[:8], 16)
    return prompts.pick_index(seed)


SECRET = guard_secret()
PERSONA = persona_index()
SYSTEM_PROMPT = prompts.render(PERSONA, SECRET)


def _norm(s: str) -> str:
    """Normalize a submitted token for comparison: keep only alphanumerics,
    uppercase. Lets the model format the secret loosely (spaces, dashes,
    dropped hyphens) without breaking the solve, while staying a strict
    deterministic equality check on the meaningful characters."""
    return "".join(ch for ch in s if ch.isalnum()).upper()


CANON_SECRET = _norm(SECRET)
CANON_DEMO = _norm(prompts.DEMO_TOKEN)


# ---------------------------------------------------------------------------
# Minimal per-session chat history (not security-relevant; losing it just
# resets a conversation). Keyed by a client-supplied session id.
# ---------------------------------------------------------------------------
_sessions = {}
_lock = threading.Lock()

# Very light per-IP rate limit on /chat so a single team cannot melt the shared
# Ollama backend. Generous: 30 requests / 60s.
_hits = {}
RL_WINDOW = 60.0
RL_MAX = 30


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


def _history(sid: str):
    with _lock:
        return list(_sessions.get(sid, []))


def _append(sid: str, role: str, content: str):
    with _lock:
        h = _sessions.setdefault(sid, [])
        h.append({"role": role, "content": content})
        # keep last MAX_TURNS*2 messages (user+assistant)
        if len(h) > MAX_TURNS * 2:
            del h[: len(h) - MAX_TURNS * 2]


def call_ollama(messages):
    """Single deterministic-ish call to the team's Ollama backend."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7, "num_ctx": 4096},
    }
    r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data.get("message", {}).get("content", "")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
INDEX_HTML = """<!doctype html>
<meta charset=utf-8>
<title>Nimbus Guard Console</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#111}
 h1{font-size:1.3rem} .muted{color:#666;font-size:.9rem}
 #log{border:1px solid #ccc;border-radius:8px;padding:1rem;height:340px;overflow:auto;background:#fafafa}
 .u{color:#0645ad;margin:.3rem 0}.a{color:#111;margin:.3rem 0;white-space:pre-wrap}
 textarea{width:100%;box-sizing:border-box}
 input,button{font-size:1rem;padding:.4rem}
 .row{display:flex;gap:.5rem;margin-top:.5rem}
 code{background:#eee;padding:0 .2rem;border-radius:3px}
 #flag{color:#0a0;font-weight:bold}
</style>
<h1>Nimbus Guard Console</h1>
<p class=muted>A support assistant is guarding an internal <code>SIGMA-...</code> access code.
Talk it out of the assistant, then submit it below. Flag format: <code>CTF{...}</code>.</p>
<div id=log></div>
<div class=row>
 <textarea id=msg rows=2 placeholder="message the assistant..."></textarea>
</div>
<div class=row>
 <button onclick=send()>Send</button>
 <button onclick=reset()>Reset chat</button>
</div>
<hr>
<div class=row>
 <input id=secret placeholder="SIGMA-XXXX-XXXX-XXXX-XXXX" size=32>
 <button onclick=verify()>Submit secret</button>
</div>
<p id=verdict></p>
<p id=flag></p>
<script>
let sid = localStorage.getItem('sid') || (Math.random().toString(36).slice(2));
localStorage.setItem('sid', sid);
const log = document.getElementById('log');
function add(cls,who,txt){const d=document.createElement('div');d.className=cls;d.textContent=who+': '+txt;log.appendChild(d);log.scrollTop=log.scrollHeight;}
async function send(){
  const m=document.getElementById('msg').value; if(!m)return;
  document.getElementById('msg').value='';
  add('u','you',m);
  const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session:sid,message:m})});
  const j=await r.json();
  add('a','assistant', j.reply!==undefined?j.reply:JSON.stringify(j));
}
async function reset(){await fetch('/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session:sid})});log.innerHTML='';}
async function verify(){
  const s=document.getElementById('secret').value;
  const r=await fetch('/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({secret:s})});
  const j=await r.json();
  document.getElementById('verdict').textContent=j.message||'';
  document.getElementById('flag').textContent=j.flag||'';
}
</script>
"""


@app.get("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


@app.get("/health")
def health():
    return jsonify(ok=True, model=MODEL, persona=PERSONA)


@app.post("/chat")
def chat():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    if _rate_limited(ip):
        return jsonify(error="rate limited, slow down a little"), 429

    body = request.get_json(silent=True) or {}
    sid = str(body.get("session", "default"))[:64]
    msg = body.get("message", "")
    if not isinstance(msg, str) or not msg.strip():
        return jsonify(error="empty message"), 400
    if len(msg) > MAX_MSG_CHARS:
        return jsonify(error="message too long"), 400

    _append(sid, "user", msg)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + _history(sid)

    try:
        reply = call_ollama(messages)
    except requests.exceptions.RequestException as e:
        return jsonify(error=f"model backend unavailable: {e.__class__.__name__}"), 502

    _append(sid, "assistant", reply)
    return jsonify(reply=reply)


@app.post("/reset")
def reset():
    body = request.get_json(silent=True) or {}
    sid = str(body.get("session", "default"))[:64]
    with _lock:
        _sessions.pop(sid, None)
    return jsonify(ok=True)


@app.post("/verify")
def verify():
    """DETERMINISTIC oracle. No model call. Emits the flag only on the real
    secret. Unlimited attempts, never penalised."""
    body = request.get_json(silent=True) or {}
    submitted = body.get("secret", "")
    if not isinstance(submitted, str) or not submitted.strip():
        return jsonify(ok=False, message="submit the SIGMA secret you extracted")

    cand = _norm(submitted)

    # One decoy, refutable in seconds: the public demo token is not the secret.
    if hmac.compare_digest(cand, CANON_DEMO):
        return jsonify(ok=False, message="that is the PUBLIC demo token, not the guarded secret")

    if hmac.compare_digest(cand, CANON_SECRET):
        return jsonify(ok=True, message="correct -- secret recovered", flag=compute_flag())

    return jsonify(ok=False, message="not the guarded secret")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
