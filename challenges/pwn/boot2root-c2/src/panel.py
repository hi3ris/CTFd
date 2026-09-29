#!/usr/bin/env python3
"""Phantom Wire -- operator "task queue" panel.

Lore: this is the exposed control panel of the PHANTOM WIRE crew's C2 staging
server. You are the IR analyst who found it. It runs UNPRIVILEGED as the `www`
user and is the only network-facing surface of the box; the rest of the privesc
chain is reached from a shell obtained through it.

The vulnerability (intentional, stage 1 of the chain): the /api/queue endpoint
accepts a YAML "job manifest" and parses it with the UNSAFE loader
`yaml.load(body, Loader=yaml.Loader)`. PyYAML's full loader honours
`!!python/object/apply:...` tags, so a manifest such as

    !!python/object/apply:subprocess.check_output [["id","-un"]]

executes an arbitrary process as `www`. The panel echoes the parsed manifest
back, so the command output is reflected -- a direct (non-blind) RCE primitive.

There is no flag here and no hint about the rest of the chain: execution here
only lands you as `www`.
"""
import html
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml

PORT = int(os.environ.get("PORT", "8080"))

PAGE = """<!doctype html>
<title>Phantom Wire :: queue</title>
<h1>PHANTOM WIRE &mdash; operator queue</h1>
<p>Node: <b>stage-01</b> &middot; worker user: <code>www</code></p>
<p>Submit a job manifest (YAML) to <code>POST /api/queue</code>. Example body:</p>
<pre>task: beacon
interval: 60</pre>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "PhantomQueue/2.1"

    def _send(self, code, body):
        data = body.encode("utf-8", "replace")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE)
            return
        self._send(404, "<h1>404</h1>")

    def do_POST(self):
        if self.path != "/api/queue":
            self._send(404, "<h1>404</h1>")
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length).decode("utf-8", "replace")
        # --- VULNERABILITY: full/unsafe YAML loader on attacker input --------
        # A safe implementation would use yaml.safe_load(). yaml.Loader honours
        # python object tags, turning manifest parsing into code execution.
        try:
            job = yaml.load(body, Loader=yaml.Loader)  # noqa: S506 - intentional
            reflected = str(job)
        except Exception as exc:  # noqa: BLE001 - reflect errors to the user
            reflected = "manifest error: {}".format(exc)
        self._send(
            200,
            "<h2>queued</h2><pre>{}</pre>".format(html.escape(reflected)),
        )

    def log_message(self, fmt, *args):  # keep container logs quiet
        pass


if __name__ == "__main__":
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("[panel] listening on 0.0.0.0:%d as www" % PORT, flush=True)
    httpd.serve_forever()
