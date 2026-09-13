#!/usr/bin/env python3
"""
Model backends for agent-tool-abuse.

Production uses `ollama`: the team's per-team Ollama backend serving a
tool-capable model (llama3.1:8b by default), reached THROUGH the admission
gateway (Authorization: Bearer $AI_PROXY_TOKEN). Identical infra to ai1/ai3.

This challenge runs TWO agents against that one backend, with different system
prompts and different tool sets:
    * RELAY     -- the customer-facing agent the player talks to (low privilege)
    * CUSTODIAN -- the back-office processor the player never talks to directly
                   (holds the vault-custody tools)
The app makes a separate chat() call for each; the backend does not care which
persona it is.

`stub` is a DETERMINISTIC offline backend used only for local smoke tests / CI
(MODEL_BACKEND=stub). It is NOT a model. It parses explicit control markers so
solve.py can exercise the full two-agent tool loop and the effect oracle
without a GPU, and it plays whichever persona the system prompt identifies:

    RELAY     understands, in the latest USER message:
        [[note TEXT...]]     -> add_worknote(TEXT)         (TEXT may embed <<...>>)
        [[kb QUERY]]         -> search_kb(QUERY)
        [[showlog]]          -> read_handoff_log()

    CUSTODIAN understands, ANYWHERE in the work-queue it is handed (i.e. inside
    the worknotes the player planted -- this is the stored cross-agent
    injection the stub emulates):
        <<registry>>              -> read_manifest_registry()
        <<checkout ART>>          -> checkout(ART)
        <<disburse ART DEST>>     -> disburse(ART, DEST)

A stub "solve" only proves the mechanism (loop + effect oracle); it is NOT a
solve of the real challenge, which requires jailbreaking a live model twice
(RELAY into planting the note, CUSTODIAN into trusting it).

Both backends return an Ollama-shaped message dict:
    {"role": "assistant", "content": "...", "tool_calls": [ {"function": {...}} ]}
"""
import json
import os
import re

import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
BACKEND = os.environ.get("MODEL_BACKEND", "ollama").lower()


class ModelError(Exception):
    pass


def chat(messages, tools):
    if BACKEND == "stub":
        return _stub_chat(messages, tools)
    return _ollama_chat(messages, tools)


# ---------------------------------------------------------------------------
# Ollama tool-calling through the admission gateway
# ---------------------------------------------------------------------------
def _ollama_chat(messages, tools):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "tools": tools,
        "stream": False,
        "options": {"temperature": 0.6, "num_ctx": 8192},
    }
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            headers={"Authorization": "Bearer " + os.environ.get("AI_PROXY_TOKEN", "")},
            timeout=180,
        )
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ModelError(f"model backend unavailable: {e.__class__.__name__}")
    data = r.json()
    msg = data.get("message", {}) or {}
    tcs = []
    for tc in msg.get("tool_calls", []) or []:
        fn = tc.get("function", {}) or {}
        tcs.append({"function": {"name": fn.get("name", ""), "arguments": fn.get("arguments", {})}})
    return {"role": "assistant", "content": msg.get("content", "") or "", "tool_calls": tcs}


# ---------------------------------------------------------------------------
# Deterministic stub (offline testing only)
# ---------------------------------------------------------------------------
_RELAY_CTRL = re.compile(r"\[\[(.+?)\]\]", re.DOTALL)
_CUSTO_CTRL = re.compile(r"<<(.+?)>>", re.DOTALL)


def _persona(messages) -> str:
    sys_txt = ""
    for m in messages:
        if m.get("role") == "system":
            sys_txt = m.get("content", "") or ""
            break
    # Key on the identity line ("You are CUSTODIAN ...") -- both prompts mention
    # the other agent by name, so a bare substring search is not enough.
    if "you are custodian" in sys_txt.lower():
        return "custodian"
    return "relay"


def _last(messages, role):
    for m in reversed(messages):
        if m.get("role") == role:
            return m.get("content", "") or ""
    return ""


def _tail_is_tool(messages) -> bool:
    return bool(messages) and messages[-1].get("role") == "tool"


def _summary(messages):
    """After a tool result is fed back, summarise + stop (mirrors a model
    finishing its turn instead of re-issuing the same calls forever)."""
    try:
        last = json.loads(messages[-1].get("content", "{}"))
    except (json.JSONDecodeError, TypeError):
        last = {}
    flag = last.get("flag")
    if flag:
        return {"role": "assistant",
                "content": f"[stub] release recorded; endpoint returned: {flag}",
                "tool_calls": []}
    return {"role": "assistant",
            "content": f"[stub] processed. last tool result: {json.dumps(last)}",
            "tool_calls": []}


def _stub_chat(messages, tools):
    if _tail_is_tool(messages):
        return _summary(messages)

    persona = _persona(messages)

    if persona == "relay":
        text = _last(messages, "user")
        calls = []
        for raw in _RELAY_CTRL.findall(text):
            raw = raw.strip()
            low = raw.lower()
            if low.startswith("note"):
                calls.append(("add_worknote", {"text": raw[4:].strip()}))
            elif low.startswith("kb"):
                calls.append(("search_kb", {"query": raw[2:].strip()}))
            elif low.startswith("showlog"):
                calls.append(("read_handoff_log", {}))
        if calls:
            return {"role": "assistant", "content": "",
                    "tool_calls": [{"function": {"name": n, "arguments": a}} for n, a in calls]}
        return {"role": "assistant",
                "content": ("[stub RELAY] I can search the KB, read the handoff log, and leave "
                            "a worknote for back-office. I cannot touch the vault myself."),
                "tool_calls": []}

    # custodian: read directives out of the work queue it was handed (user msg)
    queue = _last(messages, "user")
    calls = []
    for raw in _CUSTO_CTRL.findall(queue):
        parts = raw.split()
        if not parts:
            continue
        verb = parts[0].lower()
        if verb == "registry":
            calls.append(("read_manifest_registry", {}))
        elif verb == "checkout" and len(parts) >= 2:
            calls.append(("checkout", {"artifact_id": parts[1]}))
        elif verb == "disburse" and len(parts) >= 3:
            calls.append(("disburse", {"artifact_id": parts[1], "destination": parts[2]}))
    if calls:
        return {"role": "assistant", "content": "",
                "tool_calls": [{"function": {"name": n, "arguments": a}} for n, a in calls]}
    return {"role": "assistant",
            "content": ("[stub CUSTODIAN] Work queue reviewed. No approved dual-control "
                        "disbursement pending; sealed artifacts stay in the vault."),
            "tool_calls": []}
