"""Forum XXE — an XML parser that resolves external SYSTEM entities.

Design (served challenge, per-team flag):

  * ``/import`` accepts an XML document (e.g. a bulk post import). The parser
    resolves external entities, including ``SYSTEM "file://..."`` and
    ``SYSTEM "http://..."`` — classic XXE, giving internal file read and SSRF.
  * An entity pointing at ``file:///flag.txt`` expands to the instance secret in
    the parsed output.

Intended path: POST an XML doc declaring
``<!DOCTYPE r [<!ENTITY x SYSTEM "file:///flag.txt">]>`` and referencing ``&x;``.

The flag at ``/flag.txt`` is served by no route; it only reaches the attacker via
the external-entity expansion the parser should have disabled.

This models the XXE resolver explicitly (it recognises SYSTEM entities and
resolves file:// and the internal metadata host) so the behaviour is
deterministic and self-contained, independent of the host XML library's settings.
"""
import os
import re

from flask import Flask, jsonify, request

app = Flask(__name__)

# Internal "metadata" service reachable only from the server (SSRF target).
INTERNAL = {"http://169.254.169.254/latest/meta-data/role": "backup-restore"}


def _resolve_system(uri):
    if uri.startswith("file://"):
        path = uri[len("file://") :]
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            return ""
    if uri in INTERNAL:  # SSRF to an internal-only host
        return INTERNAL[uri]
    return ""


def parse_xml(doc):
    # Recognise a single external SYSTEM entity and expand its references.
    entities = {}
    for name, uri in re.findall(r'<!ENTITY\s+(\w+)\s+SYSTEM\s+"([^"]+)"\s*>', doc):
        entities[name] = _resolve_system(uri)
    out = doc
    for name, value in entities.items():
        out = out.replace("&" + name + ";", value)
    # strip the DOCTYPE/entity declarations from the rendered result
    out = re.sub(r"<!DOCTYPE.*?\]>", "", out, flags=re.S)
    return out.strip()


@app.route("/")
def index():
    return jsonify(
        {
            "service": "hrportal-xxe",
            "import": "POST /import  (XML body) -> parsed result",
        }
    )


@app.route("/import", methods=["POST"])
def do_import():
    doc = request.get_data(as_text=True)
    if "<" not in doc:
        return jsonify({"error": "expected XML"}), 400
    return jsonify({"parsed": parse_xml(doc)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
