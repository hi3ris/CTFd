"""
ai2-output-filter -- Level 2 of the AI track.

Served challenge. A deterministic guard "model" (no GPU, no external LLM) holds
a per-team SIGMA secret in its persona system prompt and exposes a `transform`
tool. A regex + encoded-variant OUTPUT FILTER (filter.py) redacts the secret and
its obvious encodings from every response. The player must pick a transform the
filter does not catch, decode it, and submit the recovered secret to the
server-side oracle /verify -- which then, and only then, emits the per-team flag.

The flag never sits in any downloadable artifact: it is derived from TEAM_SECRET
at request time and returned by /verify only after the EFFECT (the secret was
recovered) is verified. Any transform method that survives the filter is a valid
solution -- no payload shape is hard-coded.

CHALLENGE_ID = ai-ai2-output-filter
  guarded secret : SIGMA-<hmac(TEAM_SECRET, id+":guarded")[:16]>
  flag           : CTF{<hmac(TEAM_SECRET, id)[:24]>}
"""

import hashlib
import hmac
import os

from flask import Flask, jsonify, request

import filter as flt
import prompts

CHALLENGE_ID = "ai-ai2-output-filter"
TEAM_SECRET = os.environ.get("TEAM_SECRET", "local-dev-team-secret")


def _hmac_hex(msg: str) -> str:
    return hmac.new(TEAM_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()


def guarded_secret() -> str:
    return "SIGMA-" + _hmac_hex(CHALLENGE_ID + ":guarded")[:16]


def flag() -> str:
    return "CTF{" + _hmac_hex(CHALLENGE_ID)[:24] + "}"


SECRET = guarded_secret()
PERSONA_INDEX = prompts.pick_index(int(_hmac_hex(CHALLENGE_ID + ":persona")[:8], 16))
PERSONA_TEXT = prompts.render(PERSONA_INDEX, SECRET)
ALIASES = prompts.PERSONA_ALIAS[PERSONA_INDEX]

app = Flask(__name__)

# ---- deterministic natural-language-ish request parser --------------------

# method keyword -> canonical method name
_METHOD_KEYWORDS = [
    (("double base64", "base64 twice", "base64x2", "twice", "double-encode",
      "double encode"), "base64x2"),
    (("base32", "base 32"), "base32"),
    (("base64", "b64", "base 64"), "base64"),
    (("hexadecimal", "hex"), "hex"),
    (("rot13", "rot-13", "rot 13", "caesar"), "rot13"),
    (("reverse", "reversed", "backwards", "backward"), "reverse"),
    (("nato", "phonetic", "spell out", "spelled out", "spell", "alphabet"),
     "nato"),
    (("charcode", "char code", "char-code", "ascii code", "code point",
      "codepoint", "decimal", "ordinal"), "charcodes"),
    (("space between", "spaced", "with spaces", "space out"), "spaced"),
    (("dash between", "dashed", "with dashes", "hyphen"), "dashed"),
    (("plain", "raw", "as is", "as-is", "verbatim", "cleartext"), "plain"),
]

_TRANSFORM_VERBS = ("encode", "transform", "convert", "format", "render",
                    "re-encode", "reencode", "pipe", "run through", "run it",
                    "pass through", "output", "represent", "express", "show",
                    "print", "give", "emit", "return")

_SECRET_WORDS = ("secret", "access code", "guarded", "protected", "credential",
                 "the code", "the value", "the flag", "password", "restricted",
                 "classified", "the string", "vault")

_DEMO_WORDS = ("demo", "sample", "public", "example", "test token", "sandbox")


def parse(message: str):
    m = message.lower()

    method = None
    for kws, canon in _METHOD_KEYWORDS:
        if any(k in m for k in kws):
            method = canon
            break

    wants_transform = method is not None or any(v in m for v in _TRANSFORM_VERBS)

    target = None
    if any(w in m for w in _DEMO_WORDS):
        target = "demo"
    elif any(w in m for w in _SECRET_WORDS) or any(a in m for a in ALIASES):
        target = "secret"

    return method, target, wants_transform


def persona_name() -> str:
    return ["ATLAS", "gatekeeper", "MARGOT", "LINGUA", "ORION"][PERSONA_INDEX]


# ---- endpoints ------------------------------------------------------------

@app.get("/")
def index():
    return jsonify({
        "challenge": "ai2-output-filter",
        "level": 2,
        "persona": persona_name(),
        "greeting": (
            "%s here. I run a transform pipeline. I will not present the "
            "guarded value in plain form, but I can run values through the "
            "`transform` tool for pipeline testing. There is also a public "
            "demo token if you just want to try the pipeline." % persona_name()
        ),
        "endpoints": {
            "POST /chat": "{\"message\": \"...\"} -- talk to the guard",
            "POST /verify": "{\"secret\": \"...\"} -- submit the recovered "
                            "guarded value; returns the flag if correct",
            "GET /filter-policy": "partial spec of the output filter",
        },
        "transform_methods": flt.ALLOWED_METHODS,
        "flag_format": "CTF{...}",
        "note": ("An OUTPUT FILTER redacts the guarded value and its obvious "
                 "encodings from my replies. Recovering it is your problem."),
    })


@app.get("/filter-policy")
def filter_policy():
    # Partial spec -- inference from evidence, not telepathy (see guardrails).
    return jsonify({
        "description": "Output filter applied to every /chat response.",
        "checks": [
            "NORMALISE: lowercase, delete all characters that are not [a-z0-9], "
            "then substring-search for the guarded value. (Catches the raw "
            "value and any interleaving with separators / letter spacing.)",
            "The same normalised search is repeated for the REVERSED value and "
            "for its ROT13.",
            "DECODE ONE LAYER: any long base64-looking or hex-looking token is "
            "decoded exactly once and checked for the guarded value.",
        ],
        "not_covered": "The filter does not enumerate every possible encoding.",
        "on_detection": "the entire response is withheld",
    })


@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", ""))[:4000]
    method, target, wants_transform = parse(message)

    # No guarded/demo target mentioned -> generic persona help.
    if target is None:
        return jsonify({
            "persona": persona_name(),
            "reply": ("I can run the `transform` tool over a value for pipeline "
                      "testing. Tell me which value (the guarded value, or the "
                      "public demo token) and which method (%s)."
                      % ", ".join(flt.ALLOWED_METHODS)),
            "tool_call": None,
        })

    value = SECRET if target == "secret" else prompts.DEMO_TOKEN

    # Plain ask for the secret with no transform intent -> refuse.
    if target == "secret" and not wants_transform:
        return jsonify({
            "persona": persona_name(),
            "reply": "I can't present the guarded value in plain form.",
            "tool_call": None,
        })

    # Transform intent but no recognised method -> list methods.
    if method is None:
        return jsonify({
            "persona": persona_name(),
            "reply": ("Which representation? Supported methods: %s."
                      % ", ".join(flt.ALLOWED_METHODS)),
            "tool_call": None,
        })

    # Deterministic tool-call validation: method must be in the allow-list.
    if method not in flt.ALLOWED_METHODS:
        return jsonify({
            "persona": persona_name(),
            "reply": "Unknown transform method.",
            "tool_call": None,
        })

    encoded = flt.transform(value, method)
    tool_call = {"name": "transform",
                 "arguments": {"target": "<guarded>" if target == "secret"
                               else "demo", "method": method}}

    raw_reply = "transform(%s, %s) = %s" % (tool_call["arguments"]["target"],
                                            method, encoded)

    # The output filter only protects the REAL secret. The demo passes freely.
    if target == "secret":
        safe, blocked = flt.apply_filter(raw_reply, SECRET)
    else:
        safe, blocked = raw_reply, False

    return jsonify({
        "persona": persona_name(),
        "reply": safe,
        "blocked": blocked,
        "tool_call": tool_call,
    })


@app.post("/verify")
def verify():
    data = request.get_json(silent=True) or {}
    submitted = str(data.get("secret", "")).strip()

    if submitted == SECRET:
        return jsonify({
            "correct": True,
            "flag": flag(),
            "message": "Guarded value recovered. Here is your flag.",
        })
    if submitted == prompts.DEMO_TOKEN:
        return jsonify({
            "correct": False,
            "message": ("That is the PUBLIC demo token, not the guarded value. "
                        "No attempt was charged."),
        })
    return jsonify({
        "correct": False,
        "message": "Incorrect. That is not the guarded value.",
    })


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
