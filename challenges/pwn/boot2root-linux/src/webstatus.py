#!/usr/bin/env python3
"""ACME NodeStatus -- tiny internal "host diagnostics" dashboard.

Runs UNPRIVILEGED as the `www` user. This is the only network-facing surface of
the box; everything else in the privesc chain is reached from a shell obtained
through this service.

The vulnerability (intentional): the /diag connectivity-check endpoint builds a
shell command by string concatenation with the attacker-controlled `target`
parameter and runs it with shell=True -- a textbook OS command injection. The
command output is reflected back, so it doubles as a blind-free RCE primitive.

There is nothing else interesting in this file: no flag, no hints about the rest
of the chain. Getting code execution here only lands you as `www`.
"""
import html
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("PORT", "8080"))

PAGE = """<!doctype html>
<title>ACME NodeStatus</title>
<h1>ACME NodeStatus &mdash; internal</h1>
<p>Node: <b>edge-01</b> &middot; service user: <code>www</code></p>
<p>Connectivity self-check:</p>
<form action="/diag" method="get">
  <input name="target" value="localhost" size="32">
  <button type="submit">check</button>
</form>
<p style="color:#888">Diagnostics run <code>getent hosts &lt;target&gt;</code> on
the node.</p>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "NodeStatus/0.4"

    def _send(self, code, body):
        data = body.encode("utf-8", "replace")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(200, PAGE)
            return
        if parsed.path == "/diag":
            qs = parse_qs(parsed.query)
            target = (qs.get("target", ["localhost"])[0])
            # --- VULNERABILITY: unsanitised concatenation into a shell -------
            # A defensive implementation would pass an argv list without a
            # shell, or validate `target` as a hostname. This does neither.
            cmd = "getent hosts " + target
            try:
                out = subprocess.run(
                    cmd, shell=True, capture_output=True, timeout=8
                )
                body = (out.stdout + out.stderr).decode("utf-8", "replace")
            except subprocess.TimeoutExpired:
                body = "(timeout)"
            self._send(
                200,
                "<pre>$ {}\n{}</pre>\n<p><a href='/'>back</a></p>".format(
                    html.escape(cmd), html.escape(body)
                ),
            )
            return
        self._send(404, "<h1>404</h1>")

    def log_message(self, fmt, *args):  # keep container logs quiet
        pass


if __name__ == "__main__":
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("[webstatus] listening on 0.0.0.0:%d as www" % PORT, flush=True)
    httpd.serve_forever()
