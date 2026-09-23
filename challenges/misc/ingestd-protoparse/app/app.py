#!/usr/bin/env python3
"""Proto Fuzz Live — a homemade TLV parser with an out-of-bounds read.

Design (served challenge, per-team flag):

  * ``/parse?rec=HEX`` parses a length-prefixed record: ``[type:1][len:2 BE][value]``.
    It echoes back the parsed value.
  * The parser trusts the declared ``len`` field and reads that many bytes from a
    backing buffer that is laid out as ``value || padding || FLAG``. When the
    declared length matches the real value length you get your value back; when
    you **over-declare the length**, the read runs past the value into the
    padding and the flag — a classic out-of-bounds read.

Intended path: send a short value but a large declared length (e.g. 0x0200) so
the echoed bytes include the trailing flag.

The flag at ``/flag.txt`` is exposed by no route other than through this
over-read; a well-formed record never reveals it.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip().encode()
    except OSError:
        return b"NCTF{flag-unavailable-in-dev}"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "ingestd-protoparse",
            "parse": "/parse?rec=HEX  record = [type:1][len:2 BE][value]",
            "note": "the parser trusts the declared length",
        }
    )


@app.route("/parse")
def parse():
    try:
        rec = bytes.fromhex(request.args.get("rec", ""))
    except ValueError:
        return jsonify({"error": "rec must be hex"}), 400
    if len(rec) < 3:
        return jsonify({"error": "record too short: need type(1)+len(2)"}), 400
    rtype = rec[0]
    declared = int.from_bytes(rec[1:3], "big")
    value = rec[3:]
    # The backing buffer: the value, some padding, then the flag lives right
    # after it in memory. The parser reads `declared` bytes from here -- trusting
    # the length field instead of clamping to len(value) is the bug.
    backing = value + b"\x00" * 8 + _flag()
    out = backing[:declared]
    return jsonify({"type": rtype, "declared_len": declared, "value": out.hex()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
