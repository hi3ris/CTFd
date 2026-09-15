#!/usr/bin/env python3
"""SnapNote -- a tiny "sticky notes" preview service.

Runs UNPRIVILEGED as the `www` user. This is the only network-facing surface of
the box; the rest of the privesc chain is reached from a shell obtained through
this service.

The vulnerability (intentional, stage 1 of the chain): the /preview endpoint
renders the user-supplied note body straight through a Jinja2 template with
`Environment().from_string(body).render()`. User input IS the template, so a
note body like

    {{ cycler.__init__.__globals__.os.popen('id').read() }}

is a textbook Server-Side Template Injection and gives arbitrary code execution
as `www`. The rendered result is reflected back, so it is a direct (non-blind)
RCE primitive.

There is nothing else interesting here: no flag, no hints about the rest of the
chain. Getting execution here only lands you as `www`.
"""
import html
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from jinja2 import Environment

PORT = int(os.environ.get("PORT", "8080"))

# A single shared environment. autoescape is irrelevant to the bug: the flaw is
# that attacker input is COMPILED as a template, not merely inserted into one.
ENV = Environment()

PAGE = """<!doctype html>
<title>SnapNote</title>
<h1>SnapNote &mdash; instant sticky preview</h1>
<p>Node: <b>notes-01</b> &middot; service user: <code>www</code></p>
<p>Type a note and preview how it will render. Basic templating is supported
(e.g. <code>Hello {{ name }}</code>).</p>
<form action="/preview" method="get">
  <input name="note" value="Hello {{ 6*7 }}" size="48">
  <button type="submit">preview</button>
</form>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "SnapNote/1.2"

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
        if parsed.path == "/preview":
            qs = parse_qs(parsed.query)
            note = qs.get("note", ["Hello {{ name }}"])[0]
            # --- VULNERABILITY: user input compiled as a Jinja2 template -----
            # A safe implementation would render a FIXED template with `note`
            # passed in as data: ENV.from_string("{{ body }}").render(body=note).
            # Instead the note itself becomes the template source => SSTI.
            try:
                rendered = ENV.from_string(note).render()
            except Exception as exc:  # noqa: BLE001 - reflect errors to the user
                rendered = "template error: {}".format(exc)
            self._send(
                200,
                "<h2>preview</h2><div style='border:1px solid #ccc;padding:8px'>"
                "{}</div><p><a href='/'>back</a></p>".format(html.escape(rendered)),
            )
            return
        self._send(404, "<h1>404</h1>")

    def log_message(self, fmt, *args):  # keep container logs quiet
        pass


if __name__ == "__main__":
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("[snapnote] listening on 0.0.0.0:%d as www" % PORT, flush=True)
    httpd.serve_forever()
