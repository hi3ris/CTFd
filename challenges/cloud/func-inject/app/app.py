"""Backup Envexec — a function runtime that trusts caller-supplied environment.

Design (served challenge, per-team flag):

  * ``/invoke`` runs a named function in a tiny "serverless" runtime. The caller
    may pass ``env`` overrides. The documented, safe env keys are ``LOG_LEVEL``
    and ``REGION`` — but the runtime applies **every** key it is given, with no
    allow-list.
  * Before the function runs, the runtime consults ``INIT_HOOK`` from the
    (attacker-controllable) env and runs that hook from its registry. Passing an
    *unknown* hook returns a verbose error that leaks the registry — including a
    debug hook ``reveal`` left in by mistake, which dumps the instance secret.
  * Running the ``reveal`` init hook returns this instance's flag in the
    invocation result.

Intended path: invoke with ``env.INIT_HOOK`` set to a bogus value → read the
leaked registry from the error → re-invoke with ``env.INIT_HOOK=reveal``.

The flag at ``/flag.txt`` is served by no route; it only surfaces as the output
of the debug init hook the attacker chose to run.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

SAFE_ENV_KEYS = {"LOG_LEVEL", "REGION"}  # documented; NOT enforced below


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _hook_noop(_env):
    return None


def _hook_reveal(_env):
    # Debug hook left in the registry by mistake: dumps the instance secret.
    return _flag()


# The runtime's init-hook registry. `reveal` should never have shipped.
HOOKS = {"noop": _hook_noop, "reveal": _hook_reveal}

FUNCTIONS = {"greet", "healthcheck"}


@app.route("/")
def index():
    return jsonify(
        {
            "service": "func-inject",
            "invoke": "POST /invoke {fn, env}",
            "functions": sorted(FUNCTIONS),
            "safe_env": sorted(SAFE_ENV_KEYS),
        }
    )


@app.route("/invoke", methods=["POST"])
def invoke():
    body = request.get_json(silent=True) or {}
    fn = body.get("fn", "greet")
    env = body.get("env") or {}
    if fn not in FUNCTIONS:
        return jsonify({"error": f"no such function: {fn}"}), 404

    # BUG: env is applied wholesale, no restriction to SAFE_ENV_KEYS.
    init_hook = env.get("INIT_HOOK")
    hook_output = None
    if init_hook is not None:
        if init_hook not in HOOKS:
            # Over-verbose error leaks the registry (incl. the debug hook).
            return (
                jsonify(
                    {
                        "error": "unknown INIT_HOOK",
                        "available_hooks": sorted(HOOKS),
                    }
                ),
                400,
            )
        hook_output = HOOKS[init_hook](env)

    result = {"fn": fn, "region": env.get("REGION", "eu-west"), "ok": True}
    if hook_output is not None:
        result["init_hook_output"] = hook_output
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
