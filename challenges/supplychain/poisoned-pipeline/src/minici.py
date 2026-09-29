#!/usr/bin/env python3
"""MiniCI -- a tiny CI runner that executes user-submitted build pipelines.

Lore/supply-chain framing: this is a shared build runner. Anyone can submit a
pipeline and it runs on the runner. The deploy secret `DEPLOY_TOKEN` (the flag)
is a CI secret that is injected ONLY into steps of the `deploy` stage, and the
runner **masks** it out of the logs. That masking is the whole (broken) security
boundary.

The intended attack is the classic CI secret-exfiltration:

  * A `build`-stage step never sees `DEPLOY_TOKEN` (wrong stage).
  * A `deploy`-stage step that just `echo $DEPLOY_TOKEN` gets `***` in the logs
    (the masker redacts the literal value).
  * ...but the masker only redacts the LITERAL secret, so a `deploy` step that
    *encodes* it first -- `echo $DEPLOY_TOKEN | base64`, `| rev`, `| xxd` -- slips
    the value past the mask. Decode the log and you have the flag.

Untrusted `run:` commands execute in a controlled environment: the runner scrubs
its own flag-bearing env vars at startup, so the ONLY route to the secret is a
deploy-stage step, and only past the mask.
"""
import json
import os
import subprocess  # nosec B404 - a CI runner executes build commands by design
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import flag as flagmod

PORT = int(os.environ.get("PORT", "8080"))
FLAG = flagmod.get_flag()

# The flag is a CI secret ("DEPLOY_TOKEN"). Scrub the source env vars now so no
# build step can recover it via /proc/<runner>/environ -- the only sanctioned
# path is a deploy-stage step (which we inject it into) past the log mask.
for _k in ("FLAG", "CHALLENGE_SECRET", "TEAM_SECRET"):
    os.environ.pop(_k, None)

MAX_STEPS = 12
STEP_TIMEOUT = 8


def _mask(text: str) -> str:
    """The (broken) boundary: redact only the LITERAL secret from logs.

    This is exactly the real-world flaw: any transform of the value (base64,
    rev, hex, ...) is no longer the literal, so it sails past the mask.
    """
    if not FLAG:
        return text
    return text.replace(FLAG, "***")


def _run_pipeline(pipeline):
    logs = []
    workdir = tempfile.mkdtemp(prefix="ci-")
    for i, step in enumerate(pipeline[:MAX_STEPS]):
        if not isinstance(step, dict):
            continue
        stage = str(step.get("stage", "build"))
        run = str(step.get("run", ""))
        if not run:
            continue
        # Controlled env: a minimal PATH, plus the deploy secret ONLY for deploy.
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "CI": "true", "STAGE": stage}
        if stage == "deploy":
            env["DEPLOY_TOKEN"] = FLAG
        try:
            out = subprocess.run(  # nosec B602 - untrusted build commands, by design
                run,
                shell=True,
                cwd=workdir,
                env=env,
                capture_output=True,
                timeout=STEP_TIMEOUT,
            )
            body = (out.stdout + out.stderr).decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            body = "(step timed out)"
        logs.append(
            {
                "step": i,
                "stage": stage,
                "run": run,
                "log": _mask(body)[:8192],
            }
        )
    return logs


PAGE = """<!doctype html><meta charset="utf-8"><title>MiniCI</title>
<h1>MiniCI &mdash; shared build runner</h1>
<p>Node: <b>runner-01</b></p>
<p>Submit a pipeline to <code>POST /build</code>:</p>
<pre>{"pipeline":[
  {"stage":"build","run":"echo building..."},
  {"stage":"deploy","run":"echo deploying with $DEPLOY_TOKEN"}
]}</pre>
<p style="color:#888">Deploy steps receive the <code>DEPLOY_TOKEN</code> secret.
Secrets are masked out of build logs.</p>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "MiniCI/1.0"

    def _send(self, code, body, ctype="text/html"):
        data = body if isinstance(body, bytes) else body.encode("utf-8", "replace")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if urlparse(self.path).path in ("/", "/index.html"):
            self._send(200, PAGE)
            return
        self._send(404, "<h1>404</h1>")

    def do_POST(self):
        if urlparse(self.path).path != "/build":
            self._send(404, "<h1>404</h1>")
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode("utf-8", "replace")) if raw else {}
            pipeline = body.get("pipeline", [])
            if not isinstance(pipeline, list):
                raise ValueError("pipeline must be a list")
        except ValueError as e:
            self._send(400, json.dumps({"error": str(e)}), "application/json")
            return
        logs = _run_pipeline(pipeline)
        self._send(200, json.dumps({"result": "ok", "steps": logs}), "application/json")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)  # nosec B104
    print("[minici] listening on 0.0.0.0:%d" % PORT, flush=True)
    httpd.serve_forever()
