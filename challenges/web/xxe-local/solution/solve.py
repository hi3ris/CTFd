#!/usr/bin/env python3
"""Resolve the XXE external entity locally against the shipped files."""

import io
import os
import xml.sax
from xml.sax import ContentHandler, InputSource
from xml.sax.handler import feature_external_ges

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


class LocalResolver:
    def resolveEntity(self, public_id, system_id):
        # SYSTEM ids are relative -- resolve them against the shipped dir.
        path = os.path.join(ROOT, os.path.basename(system_id))
        src = InputSource()
        src.setByteStream(io.BytesIO(open(path, "rb").read()))
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


def main() -> None:
    data = open(os.path.join(ROOT, "invoice.xml"), "rb").read()
    parser = xml.sax.make_parser()
    parser.setFeature(feature_external_ges, True)
    parser.setEntityResolver(LocalResolver())
    handler = NoteHandler()
    parser.setContentHandler(handler)
    parser.parse(io.BytesIO(data))
    print("".join(handler.note).strip())


if __name__ == "__main__":
    main()
