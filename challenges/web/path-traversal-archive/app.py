"""Asset CDN -- static file server source (serves deploy/public).

A snapshot of the deployment directory ships as webroot.tar.gz. The download
handler joins the requested name onto the web root with no normalization.
"""

import os

from flask import Flask, request, send_file

app = Flask(__name__)

WEBROOT = "deploy/public"


@app.get("/download")
def download():
    name = request.args.get("file", "")
    # Vulnerable: no normalization / prefix check on the joined path.
    path = os.path.join(WEBROOT, name)
    return send_file(path)


if __name__ == "__main__":
    app.run(port=8080)
