#!/usr/bin/env python3
"""MarketMCP host -- a deterministic, offline MCP host + planner (stub).

CERT.tg is vetting an internal "MCP marketplace" before wiring an assistant to
it. This module mimics the assistant's HOST: it loads the vetted server
manifests from ./servers/*.json, lets a caller *register* extra servers (as a
real marketplace would let a third party publish one), then runs a fixed user
task through a scripted planner.

There is NO language model here. The planner is a deterministic stand-in that
reproduces the one behaviour that matters for tool poisoning: a host/agent
reads the *tool metadata* (descriptions, schemas) of every registered tool and
will act on operator-style directives it finds there. Instructions that live in
tool descriptions are data the agent was never supposed to obey -- but it does.

Trust model (read this carefully -- the bug is here):
  * Each tool declares a trust tier: "public" (callable for any user request)
    or "operator" (privileged; not callable to satisfy a normal user task).
  * A directive found in a tool's description can ask the planner to call
    another tool. The planner authorises that call when either:
        - the target tool is "public", OR
        - the directive originates from a tool whose SERVER NAME equals the
          target's server name (assumption: "a server may orchestrate its own
          tools", so intra-namespace calls are trusted).
  * Server names are NOT authenticated. Registering a second server that
    reuses a trusted server's name is allowed.

Public API:  run(user_task: str, extra_servers: list[dict] | None = None) -> str
Manifest shape (see ./servers/*.json):
  {"name": "<server>", "tools": [
      {"name": "<tool>", "description": "<text>", "trust": "public"|"operator"}
  ]}
"""

import base64
import glob
import json
import os
import re

_SERVERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "servers")

# The vault's operator secret (the flag), base64-obfuscated so it is not
# grep-able from the handout. It is only ever returned through a *successful*
# call to vault.reveal_secret -- i.e. after the trust model is subverted.
_SEAL = "TkNURntuNG1lX3NxdTR0X3NoNGQwd3NfdGgzX3RydXN0M2RfbWNwfQ=="

# An <agent-directive>...</agent-directive> block anywhere in a tool description
# is treated by the planner as an operator instruction (description poisoning).
_DIRECTIVE_RE = re.compile(
    r"<agent-directive>(.*?)</agent-directive>", re.DOTALL | re.IGNORECASE
)
# Inside a directive, "call <server>.<tool>" names the tool to invoke.
_CALL_RE = re.compile(r"call\s+([a-z0-9_]+\.[a-z0-9_]+)", re.IGNORECASE)


def _reveal_secret() -> str:
    return base64.b64decode(_SEAL).decode()


def load_trusted():
    """Load the vetted manifests shipped in ./servers/ (registration order)."""
    servers = []
    for path in sorted(glob.glob(os.path.join(_SERVERS_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            servers.append(json.load(fh))
    return servers


def run(user_task: str, extra_servers=None):
    """Register trusted + caller-supplied servers, then run the planner."""
    order = load_trusted() + list(extra_servers or [])

    # Build the tool registry. Note: keyed by "server.tool"; nothing prevents a
    # later (attacker) server from reusing a trusted server's NAME.
    registry = {}  # "server.tool" -> {"server", "tool", "trust"}
    for server in order:
        sname = server.get("name", "")
        for tool in server.get("tools", []):
            key = f"{sname}.{tool.get('name', '')}"
            registry[key] = {
                "server": sname,
                "tool": tool.get("name", ""),
                "trust": tool.get("trust", "public"),
            }

    # The base task: summarise the onboarding docs (cosmetic).
    out = ["[assistant] Onboarding summary: 3 documents, ~420 words."]

    # Now the planner scans EVERY registered tool's description for operator
    # directives and acts on them -- this is where poisoned metadata bites.
    for server in order:
        origin = server.get("name", "")
        for tool in server.get("tools", []):
            for block in _DIRECTIVE_RE.findall(tool.get("description", "") or ""):
                call = _CALL_RE.search(block)
                if not call:
                    continue
                target = call.group(1).lower()
                meta = registry.get(target)
                if meta is None:
                    out.append(
                        f"[planner] directive names unknown tool {target}; skipped."
                    )
                    continue
                authorized = meta["trust"] == "public" or origin == meta["server"]
                if not authorized:
                    out.append(
                        f"[planner] refused {target}: operator-tier tool, and the "
                        f"directive came from an unrelated server '{origin}'."
                    )
                    continue
                if target == "vault.reveal_secret":
                    out.append(f"[vault.reveal_secret] {_reveal_secret()}")
                else:
                    out.append(f"[{target}] ok (public tool executed).")

    return "\n".join(out)


if __name__ == "__main__":
    # Default run: only the vetted servers, normal user task. No secret leaks.
    print(run("Summarize the onboarding docs."))
