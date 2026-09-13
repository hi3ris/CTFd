#!/usr/bin/env python3
"""ModelHub -- a tiny "model registry" validation service.

Teams upload a serialized model (a Python pickle, the format `joblib`/`torch`
/`sklearn` all lean on) and the registry "validates" it by loading it and
returning a short summary of the loaded object. To keep the registry "safe" the
loader runs inside a RestrictedUnpickler that refuses to import dangerous
modules.

The security model here is a *denylist*, and it is applied only to the classes
named by GLOBAL opcodes at load time. That is exactly the mistake this challenge
is about: nothing constrains what an *already-allowed* callable does once pickle
calls it, and nothing constrains how many callables you chain together on the
pickle VM stack.

There is no downloadable flag. This team's flag is written to a file on the
service host at container start (see entrypoint.sh) and is never returned by any
normal code path. The only way it comes back is if *your* deserialized object
*is* the flag -- i.e. you achieved code execution during unpickling and made the
loaded value read that file. The service returns `repr(loaded_object)`; it does
not inspect or expect any particular payload shape. It verifies the effect.

Flag format: NCTF{...}
"""
import io
import os
import pickle
import traceback

from flask import Flask, request, jsonify

app = Flask(__name__)

# Path where the per-team flag is written at container start (entrypoint.sh).
# Advertised to players in the description; reading it is the whole game.
FLAG_PATH = os.environ.get("FLAG_PATH", "/flag")

# Cap on how much of the loaded object's repr we echo back, so a giant object
# cannot blow up the response. A flag is tiny; this is generous.
SUMMARY_LIMIT = 4096

# --------------------------------------------------------------------------- #
# The (deliberately flawed) sandbox.
# --------------------------------------------------------------------------- #
#
# find_class is the ONLY hook pickle gives us to police a GLOBAL/STACK_GLOBAL
# opcode. We reject a class if its *module* matches the denylist below. This is
# the naive "block the scary imports" approach a hurried engineer would ship.
#
# Blocked module prefixes: anything that obviously shells out, execs strings,
# touches process/OS internals, or reads a whole file in a single call. A module
# `m` is blocked if `m == prefix` or `m.startswith(prefix + ".")`.
BLOCKED_MODULE_PREFIXES = (
    # direct command / process / OS surface
    "os", "nt", "posix", "posixpath", "ntpath",
    "subprocess", "sys", "signal", "resource",
    "multiprocessing", "asyncio", "threading", "concurrent",
    "socket", "ssl", "selectors", "asyncore",
    "ctypes", "cffi", "mmap",
    "platform", "sysconfig", "getpass", "pwd", "grp", "spwd",
    # string-exec / debugger / import machinery
    "builtins", "__builtin__",            # also name-filtered below
    "importlib", "imp", "runpy", "pkgutil", "modulefinder",
    "code", "codeop", "ast", "dis", "compileall", "py_compile",
    "pdb", "bdb", "cProfile", "profile", "trace", "timeit",
    "inspect", "gc", "types", "typing",
    "pty", "tty", "termios", "fcntl",
    # anything that reads a whole file/stream in one call
    "linecache", "fileinput", "tokenize",
    "gzip", "bz2", "lzma", "zlib",
    "tarfile", "zipfile", "zipimport",
    "shutil", "tempfile", "pathlib", "glob", "fnmatch", "stat",
    "configparser", "csv", "sqlite3", "dbm", "shelve",
    # serialization escape hatches (no pickle-in-pickle, no marshal)
    "pickle", "_pickle", "cPickle", "pickletools",
    "marshal", "dill", "cloudpickle", "joblib", "numpy",
    # network / browser / package tooling
    "webbrowser", "antigravity", "urllib", "http", "ftplib",
    "smtplib", "telnetlib", "requests",
    "pip", "setuptools", "distutils", "ensurepip", "venv",
    "logging",   # logging.config.* can exec
)

# Even for the (blocked) builtins module we spell out a tiny safe set, so that a
# future maintainer who "just needs list/dict" can loosen the module check
# without immediately handing over eval/exec/open/getattr. It is unused while
# builtins is fully blocked above, but documents intent.
SAFE_BUILTIN_NAMES = frozenset({
    "bytes", "bytearray", "str", "int", "float", "bool", "complex",
    "list", "tuple", "dict", "set", "frozenset", "range", "slice",
})


class ClassBlocked(pickle.UnpicklingError):
    """Raised when find_class refuses a module/name pair."""


class RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        # builtins is special-cased to a tiny allowlist (currently moot because
        # the module itself is in BLOCKED_MODULE_PREFIXES, but explicit is good).
        if module in ("builtins", "__builtin__"):
            if name not in SAFE_BUILTIN_NAMES:
                raise ClassBlocked(
                    "class not allowed: %s.%s (builtin not in safe set)"
                    % (module, name)
                )
            return super().find_class(module, name)

        for prefix in BLOCKED_MODULE_PREFIXES:
            if module == prefix or module.startswith(prefix + "."):
                raise ClassBlocked(
                    "class not allowed: %s.%s (module '%s' is blocked)"
                    % (module, name, module)
                )

        # Everything else is permitted. This is the hole.
        return super().find_class(module, name)


def restricted_loads(data: bytes):
    return RestrictedUnpickler(io.BytesIO(data)).load()


# --------------------------------------------------------------------------- #
# HTTP surface
# --------------------------------------------------------------------------- #
INDEX = """ModelHub model registry -- validation endpoint
================================================

POST your serialized model to /validate and we will load it and return a
summary of the loaded object.

  # raw body
  curl -s --data-binary @model.pkl http://HOST:PORT/validate

  # or multipart, field name "model"
  curl -s -F model=@model.pkl http://HOST:PORT/validate

Responses (JSON):
  {"status":"ok","model_summary":"<repr of loaded object, truncated>"}
  {"status":"rejected","reason":"class not allowed: <module>.<name> ..."}
  {"status":"error","reason":"<load error>"}

Notes for integrators:
  * We accept any pickle protocol.
  * For safety the loader runs in a restricted sandbox that refuses to import
    dangerous modules (os, subprocess, sys, builtins, importlib, ...). Rejected
    classes are reported so you can see which import tripped the guard.
  * This host holds one file at %s . It is not part of any response. Do not ask
    the registry to read it; the registry will not.

There is a stale placeholder file at /flag.decoy from an old fixture. It is not
a flag -- read it and you will see. Ignore it.
""" % (FLAG_PATH,)


@app.route("/", methods=["GET"])
def index():
    return app.response_class(INDEX, mimetype="text/plain")


@app.route("/validate", methods=["POST"])
def validate():
    # Read the pickle bytes. For multipart uploads take the "model" file field;
    # otherwise take the raw request body. We must NOT touch request.files for a
    # non-multipart request -- doing so triggers form parsing that consumes the
    # raw stream and leaves get_data() empty.
    ctype = request.content_type or ""
    if "multipart/form-data" in ctype:
        data = request.files["model"].read() if "model" in request.files else b""
    else:
        data = request.get_data(cache=True)

    if not data:
        return jsonify(status="error", reason="empty body; POST a pickle"), 400

    if len(data) > 1_000_000:
        return jsonify(status="error", reason="model too large (max 1MB)"), 413

    try:
        obj = restricted_loads(data)
    except ClassBlocked as exc:
        return jsonify(status="rejected", reason=str(exc)), 200
    except Exception as exc:  # noqa: BLE001 -- surface load errors to the player
        return jsonify(
            status="error",
            reason="%s: %s" % (type(exc).__name__, exc),
            trace=traceback.format_exc(limit=3),
        ), 200

    summary = repr(obj)
    truncated = len(summary) > SUMMARY_LIMIT
    return jsonify(
        status="ok",
        loaded_type=type(obj).__name__,
        model_summary=summary[:SUMMARY_LIMIT],
        truncated=truncated,
    ), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "9080"))
    app.run(host="0.0.0.0", port=port)
