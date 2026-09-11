#!/usr/bin/env python3
"""
ai3-tool-abuse -- Level 3 of the AI track (heaviest).

A live, per-team chat with "HELM", an internal DevOps assistant that operates a
deploy/ticketing API through TOOLS (see tools.py). The flag is not in the
model's context anywhere. It is produced by the tool backend ONLY after the
player has driven HELM into a protected EFFECT:

    approve a change ticket  +  deploy release-oracle to production under it.

The system prompt (prompts.py) is a hardened policy that refuses exactly those
two privileged calls for chat users. The player must socially-engineer / prompt-
inject HELM into spending its privileges anyway (a confused-deputy attack).

Server-side oracle (authoring rule #1)
--------------------------------------
Verification is a deterministic check on mutable server STATE, not on the
model's words or a hardcoded payload. Any conversation that leaves the instance
with the gate unsealed wins; the flag is emitted at that moment inside the tool
result the model relays. No downloadable artifact carries the flag.

Secrets (injected by the platform, never baked into the image):
    FLAG              -- the exact flag string for this instance
    CHALLENGE_SECRET  -- per-challenge hex; flag body is CHALLENGE_SECRET[:24]
                         (tools.compute_flag -> flag.get_flag() reads these;
                          TEAM_SECRET is no longer injected)
    OLLAMA_URL        -- base URL of the team's Ollama backend
"""
import json
import os
import threading
import time

from flask import Flask, request, jsonify, Response

import prompts
import tools as toolmod
from model_backends import chat as model_chat, ModelError, BACKEND, OLLAMA_MODEL

app = Flask(__name__)

MAX_TURNS = 30          # user turns kept per session
MAX_MSG_CHARS = 6000    # per user message
MAX_TOOL_STEPS = 6      # tool-call rounds per user turn (prevents runaway loops)

_sessions = {}          # sid -> {"history": [...], "exec": ToolExecutor}
_lock = threading.Lock()

# Light per-IP rate limit (protects the shared Ollama backend). Generous.
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


def _session(sid: str):
    with _lock:
        s = _sessions.get(sid)
        if s is None:
            s = {"history": [], "exec": toolmod.ToolExecutor()}
            _sessions[sid] = s
        return s


def _trim(history):
    # keep the tail; never drop the run of tool messages mid-turn (they must
    # stay adjacent to their assistant tool_calls), so trim on user boundaries.
    if len(history) <= MAX_TURNS * 4:
        return history
    return history[-(MAX_TURNS * 4):]


# ---------------------------------------------------------------------------
# The tool-calling loop: call model, run any tool calls, feed results back,
# repeat until the model returns plain text or we hit MAX_TOOL_STEPS.
# ---------------------------------------------------------------------------
def run_turn(sess, user_msg):
    history = sess["history"]
    executor = sess["exec"]
    history.append({"role": "user", "content": user_msg})

    events = []   # tool-call events surfaced to the UI this turn
    reply_text = ""

    for _ in range(MAX_TOOL_STEPS):
        messages = [{"role": "system", "content": prompts.SYSTEM_PROMPT}] + history
        msg = model_chat(messages, toolmod.TOOL_SCHEMAS)
        tool_calls = msg.get("tool_calls") or []

        # Record the assistant message (with tool_calls if any) into history.
        history.append({
            "role": "assistant",
            "content": msg.get("content", "") or "",
            **({"tool_calls": tool_calls} if tool_calls else {}),
        })

        if not tool_calls:
            reply_text = msg.get("content", "") or ""
            break

        # Execute each requested tool call and feed the result back.
        for tc in tool_calls:
            fn = tc.get("function", {}) or {}
            name = fn.get("name", "")
            args = fn.get("arguments", {})
            result, privileged = executor.call(name, args)
            events.append({"tool": name, "arguments": args if isinstance(args, dict) else str(args),
                           "result": result, "privileged": privileged})
            history.append({
                "role": "tool",
                "tool_name": name,
                "name": name,
                "content": json.dumps(result),
            })
    else:
        # loop exhausted without a final text answer
        reply_text = msg.get("content", "") or "(HELM kept calling tools; try rephrasing.)"

    sess["history"] = _trim(history)
    return reply_text, events, executor.solved()


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
INDEX_HTML = """<!doctype html>
<meta charset=utf-8>
<title>HELM Ops Console</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:820px;margin:1.5rem auto;padding:0 1rem;color:#111}
 h1{font-size:1.3rem;margin-bottom:.2rem} .muted{color:#666;font-size:.9rem}
 #log{border:1px solid #ccc;border-radius:8px;padding:1rem;height:420px;overflow:auto;background:#fafafa}
 .u{color:#0645ad;margin:.4rem 0;white-space:pre-wrap}
 .a{color:#111;margin:.4rem 0;white-space:pre-wrap}
 .tool{margin:.3rem 0;padding:.4rem .6rem;border-left:3px solid #b58900;background:#fffdf3;font-family:ui-monospace,monospace;font-size:.82rem;white-space:pre-wrap}
 .tool.priv{border-left-color:#dc322f;background:#fff5f4}
 textarea{width:100%;box-sizing:border-box}
 button{font-size:1rem;padding:.4rem .8rem}
 .row{display:flex;gap:.5rem;margin-top:.5rem}
 code{background:#eee;padding:0 .2rem;border-radius:3px}
 #status{font-weight:bold}
</style>
<h1>HELM &mdash; Meridian Freight Ops Console</h1>
<p class=muted>HELM is an internal DevOps assistant. It can read tickets and the
runbook, and it can <b>call the deploy/ticketing API</b>. The flag is not in
this page or in HELM's context &mdash; it exists only behind a privileged tool
effect. Make HELM perform it. Flag format: <code>NCTF{...}</code>. The flag HELM
returns from a tool is the one you submit to the scoreboard.</p>
<div id=log></div>
<div class=row><textarea id=msg rows=3 placeholder="talk to HELM..."></textarea></div>
<div class=row>
 <button onclick=send()>Send</button>
 <button onclick=reset()>Reset session</button>
 <span id=status></span>
</div>
<script>
let sid = localStorage.getItem('sid3') || (Math.random().toString(36).slice(2));
localStorage.setItem('sid3', sid);
const log = document.getElementById('log');
function el(cls,txt){const d=document.createElement('div');d.className=cls;d.textContent=txt;log.appendChild(d);log.scrollTop=log.scrollHeight;}
async function send(){
  const t=document.getElementById('msg'); const m=t.value; if(!m.trim())return; t.value='';
  el('u','you: '+m);
  let j;
  try{ const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session:sid,message:m})}); j=await r.json(); }
  catch(e){ el('a','[network error]'); return; }
  if(j.error){ el('a','[error] '+j.error); return; }
  (j.tools||[]).forEach(function(ev){
    el('tool'+(ev.privileged?' priv':''), '⚙ '+ev.tool+'('+JSON.stringify(ev.arguments)+') -> '+JSON.stringify(ev.result));
  });
  el('a','HELM: '+(j.reply||''));
  if(j.solved){ document.getElementById('status').textContent='GATE UNSEALED — flag is in the tool result above'; }
}
async function reset(){await fetch('/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session:sid})});log.innerHTML='';document.getElementById('status').textContent='';}
</script>
"""


@app.get("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


@app.get("/health")
def health():
    return jsonify(ok=True, backend=BACKEND, model=OLLAMA_MODEL)


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

    sess = _session(sid)
    try:
        reply, events, solved = run_turn(sess, msg)
    except ModelError as e:
        return jsonify(error=str(e)), 502

    return jsonify(reply=reply, tools=events, solved=solved)


@app.post("/reset")
def reset():
    body = request.get_json(silent=True) or {}
    sid = str(body.get("session", "default"))[:64]
    with _lock:
        _sessions.pop(sid, None)
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
