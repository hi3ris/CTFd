"""Relay — a chain: reverse a homemade TLV protocol → hidden op → over-read.

Design (served challenge, per-team flag):

  * ``/cmd`` takes a hex-encoded packet in the homemade TLV format
    ``TT LL <value…>`` (1 byte type, 1 byte length, then ``length`` bytes).
    Documented ops: ``0x01`` ping, ``0x02`` echo.
  * The echo op copies ``length`` bytes out of a fixed buffer that holds the
    request value **followed by the instance secret**. A ``length`` larger than
    the value you supplied over-reads into the secret (a classic OOB read), so
    the flag bleeds into the echo response.

Reverse the framing (the ``/`` help hints at TLV), then send an echo whose
declared length exceeds its payload. The flag at ``/flag.txt`` is served by no
route; it only leaks through the over-read.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

BUFSIZE = 256


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


@app.route("/")
def index():
    return jsonify(
        {
            "service": "relay",
            "cmd": "POST /cmd  {packet: '<hex>'}  format: TT LL VALUE",
            "ops": {"0x01": "ping", "0x02": "echo"},
        }
    )


@app.route("/cmd", methods=["POST"])
def cmd():
    b = request.get_json(silent=True) or {}
    try:
        raw = bytes.fromhex(b.get("packet", ""))
    except ValueError:
        return jsonify({"error": "packet must be hex"}), 400
    if len(raw) < 2:
        return jsonify({"error": "short packet"}), 400
    typ, length = raw[0], raw[1]
    value = raw[2:]

    if typ == 0x01:
        return jsonify({"op": "ping", "reply": "pong"})

    if typ == 0x02:
        # Fixed buffer: [ value | secret | padding ]. Copy out `length` bytes.
        # BUG: no bound check against len(value) → over-read into the secret.
        buf = bytearray(BUFSIZE)
        payload = value + b"\x00" + _flag().encode()
        buf[: len(payload)] = payload[:BUFSIZE]
        out = bytes(buf[:length])
        return jsonify({"op": "echo", "data": out.decode("latin-1")})

    return jsonify({"error": f"unknown op {typ:#04x}"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
