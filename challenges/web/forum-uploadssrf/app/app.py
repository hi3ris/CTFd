"""CMS Uploadssrf — an upload filter bypass that feeds a server-side renderer.

Design (served challenge, per-team flag):

  * ``/upload`` accepts a "document" and only allows ``.png`` — but it checks the
    extension on the *declared* filename, so ``report.png.svg`` (or any name
    ending ``.png`` with SVG content) slips through.
  * The uploaded document is rendered server-side. The renderer fetches any URL
    referenced by ``render:<url>`` in the content — an SSRF. The internal
    metadata host returns a role credential and, at ``/latest/meta-data/flag``,
    the instance secret.

Intended path: upload a doc that bypasses the extension check and contains
``render:http://169.254.169.254/latest/meta-data/flag``.

The flag at ``/flag.txt`` is exposed only through the internal metadata host the
renderer's SSRF reaches.
"""
import os
import re

from flask import Flask, jsonify, request

app = Flask(__name__)


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


# Internal metadata service (reachable only server-side).
def _metadata(url):
    table = {
        "http://169.254.169.254/latest/meta-data/role": "backup-restore",
        "http://169.254.169.254/latest/meta-data/flag": _flag(),
    }
    return table.get(url)


def _allowed(filename):
    # BUG: only checks that the name ends with .png, ignoring real content type
    # and double extensions.
    return filename.endswith(".png")


@app.route("/")
def index():
    return jsonify(
        {
            "service": "forum-uploadssrf",
            "upload": "POST /upload {filename, content}",
            "note": "only .png documents are accepted",
        }
    )


@app.route("/upload", methods=["POST"])
def upload():
    body = request.get_json(silent=True) or {}
    filename = body.get("filename", "")
    content = body.get("content", "")
    if not _allowed(filename):
        return jsonify({"error": "only .png allowed"}), 400
    # Server-side render: follow any render:<url> directive (SSRF).
    m = re.search(r"render:(\S+)", content)
    rendered = None
    if m:
        rendered = _metadata(m.group(1))
        if rendered is None:
            rendered = f"<fetched {m.group(1)}>"
    return jsonify({"stored": filename, "rendered": rendered})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
