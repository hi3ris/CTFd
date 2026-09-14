"""Invoice ingest endpoint -- source handout.

The endpoint parses uploaded XML with external general entities ENABLED and a
resolver that reads SYSTEM ids from the app working directory. A captured
upload (invoice.xml) is shipped, along with the server's working directory
contents (secret.flag lives there).
"""

import io
import xml.sax
from xml.sax import ContentHandler, InputSource
from xml.sax.handler import feature_external_ges

from flask import Flask, jsonify, request

app = Flask(__name__)


class LocalResolver:
    # Resolves SYSTEM entity ids against local files in the working directory.
    def resolveEntity(self, public_id, system_id):
        src = InputSource()
        src.setByteStream(io.BytesIO(open(system_id, "rb").read()))
        return src


class NoteHandler(ContentHandler):
    def __init__(self):
        super().__init__()
        self.in_note = False
        self.note = []

    def startElement(self, name, attrs):
        self.in_note = name == "note"

    def endElement(self, name):
        self.in_note = False

    def characters(self, content):
        if self.in_note:
            self.note.append(content)


@app.post("/invoice")
def invoice():
    data = request.get_data()
    parser = xml.sax.make_parser()
    # Vulnerable: external general entities are turned on.
    parser.setFeature(feature_external_ges, True)
    parser.setEntityResolver(LocalResolver())
    handler = NoteHandler()
    parser.setContentHandler(handler)
    parser.parse(io.BytesIO(data))
    return jsonify(note="".join(handler.note).strip())


if __name__ == "__main__":
    app.run(port=8080)
