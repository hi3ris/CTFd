#!/usr/bin/env python3
"""Graph Climb — a homegrown GraphQL-style API with an IDOR + mass-assignment chain.

Design (served challenge, per-team flag):

  * ``POST /graphql`` with ``{"query": "...", "variables": {...}}`` speaks a small
    GraphQL-style language. Introspection (``__schema``) is enabled and reveals
    the type/field/mutation names — including a ``flag`` field gated on the
    viewer's role and a ``updateUser`` mutation.
  * You authenticate as a low-privilege user via the ``X-Session`` header (any
    value mints a fresh ``role=user`` viewer bound to id 1000).
  * IDOR: ``user(id)`` returns any user by id, with no authorization check, so you
    can enumerate accounts and learn the shape (there is an ``admin`` account).
  * Mass-assignment: ``updateUser`` writes **every** field supplied in
    ``patch`` — including ``role`` — onto the target user, again with no check.
  * ``viewer { flag }`` returns this instance's flag only when the viewer's role
    is ``admin``.

Intended path: introspect, promote yourself with
``updateUser(id: 1000, patch: {role: "admin"})``, then read ``viewer { flag }``.

The flag at ``/flag.txt`` is exposed by no route other than the role-gated
``flag`` field; there is no query that returns it without an admin viewer.

The query language is intentionally tiny (this is a challenge, not a spec): a
single top-level selection, ``name(arg: value, ...) { subfields }``, plus the
``__schema`` introspection keyword. Values are JSON scalars or ``$variables``.
"""
import json
import os
import re
import uuid

from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory user store. id 1000 is the viewer bootstrap; 'admin' account exists so
# the shape is discoverable via IDOR, but promoting *yourself* is the real path.
USERS = {
    1000: {"id": 1000, "name": "guest", "role": "user"},
    1: {"id": 1, "name": "admin", "role": "admin"},
}

SCHEMA = {
    "queryType": "Query",
    "types": [
        {
            "name": "Query",
            "fields": [
                {"name": "user", "args": ["id"], "type": "User"},
                {"name": "viewer", "args": [], "type": "Viewer"},
                {"name": "__schema", "args": [], "type": "__Schema"},
            ],
        },
        {
            "name": "Mutation",
            "fields": [
                {"name": "updateUser", "args": ["id", "patch"], "type": "User"},
            ],
        },
        {
            "name": "User",
            "fields": [
                {"name": "id", "args": [], "type": "Int"},
                {"name": "name", "args": [], "type": "String"},
                {"name": "role", "args": [], "type": "String"},
            ],
        },
        {
            "name": "Viewer",
            "fields": [
                {"name": "id", "args": [], "type": "Int"},
                {"name": "role", "args": [], "type": "String"},
                {"name": "flag", "args": [], "type": "String  # admin only"},
            ],
        },
    ],
}

# Very small selection parser: name(args) { fields }
_SEL = re.compile(
    r"^\s*(?P<name>\w+)\s*(?:\((?P<args>.*?)\))?\s*(?:\{(?P<sub>.*)\})?\s*$", re.S
)


def _viewer_id():
    # Any session header binds to the bootstrap guest (id 1000) for this challenge.
    return 1000 if request.headers.get("X-Session") else None


def _parse_args(raw, variables):
    """Parse ``k: value, k2: value2`` where value is a JSON scalar/object or $var."""
    if not raw or not raw.strip():
        return {}
    out = {}
    depth = 0
    buf = ""
    parts = []
    for ch in raw:
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf)
    for part in parts:
        k, _, v = part.partition(":")
        k, v = k.strip(), v.strip()
        if not k:
            continue
        if v.startswith("$"):
            out[k] = variables.get(v[1:])
        else:
            try:
                out[k] = json.loads(v)
            except json.JSONDecodeError:
                out[k] = v.strip('"')
    return out


def _pick(obj, sub):
    if not sub or not sub.strip():
        return obj
    fields = [f.strip() for f in re.split(r"[\s,]+", sub.strip()) if f.strip()]
    return {f: obj.get(f) for f in fields}


def _resolve(name, args, sub):
    if name == "__schema":
        return SCHEMA
    if name == "user":
        uid = args.get("id")
        u = USERS.get(uid if isinstance(uid, int) else -1)
        if not u:
            return {"error": "no such user"}
        return _pick(u, sub)  # IDOR: no authz on reading arbitrary users
    if name == "viewer":
        vid = _viewer_id()
        if vid is None:
            return {"error": "no session"}
        u = USERS[vid]
        view = {"id": u["id"], "role": u["role"]}
        if "flag" in (sub or ""):
            if u["role"] == "admin":
                try:
                    with open("/flag.txt", encoding="utf-8") as fh:
                        view["flag"] = fh.read().strip()
                except OSError:
                    view["flag"] = None
            else:
                view["flag"] = "<admin only>"
        return _pick(view, sub) if sub else view
    if name == "updateUser":
        uid = args.get("id")
        patch = args.get("patch") or {}
        u = USERS.get(uid if isinstance(uid, int) else -1)
        if not u:
            return {"error": "no such user"}
        # Mass-assignment: every supplied field is written, role included.
        for k, v in patch.items():
            if k != "id":
                u[k] = v
        return _pick(u, sub)
    return {"error": "unknown field: " + name}


@app.route("/")
def index():
    return jsonify(
        {
            "service": "graph-climb",
            "graphql": "POST /graphql {query, variables}; set X-Session header",
            "introspection": 'query "{ __schema { ... } }"',
        }
    )


@app.route("/graphql", methods=["POST"])
def graphql():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    variables = data.get("variables") or {}
    body = query.strip()
    if body.startswith("mutation") or body.startswith("query"):
        body = body.split(None, 1)[1] if " " in body else ""
    body = body.strip()
    if body.startswith("{") and body.endswith("}"):
        body = body[1:-1].strip()
    m = _SEL.match(body)
    if not m:
        return jsonify({"errors": [{"message": "parse error"}]}), 400
    name = m.group("name")
    args = _parse_args(m.group("args"), variables)
    sub = m.group("sub")
    return jsonify({"data": {name: _resolve(name, args, sub)}})


if __name__ == "__main__":
    # New viewer identity per process so a restart doesn't keep a promoted role.
    USERS[1000]["role"] = "user"
    USERS[1000]["_boot"] = str(uuid.uuid4())
    del USERS[1000]["_boot"]
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
