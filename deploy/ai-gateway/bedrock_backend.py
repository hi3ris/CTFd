"""Amazon Bedrock backend for the AI gateway.

The gateway speaks Ollama's ``/api/chat`` dialect to the challenge containers
(that is what the 3 model-driven AI challenges send and parse). This module
translates that dialect to the Bedrock Converse API and back, so the whole AI
track can run WITHOUT the GPU node when the "G and VT" EC2 quota is refused:

    Ollama request  --to_converse()-->  Converse kwargs
    Converse reply  --from_converse()-> Ollama-shaped reply (message.content,
                                        message.tool_calls, prompt_eval_count,
                                        eval_count)

The translation functions are pure (no network) and unit-tested in
tests/test_ai_gateway_bedrock.py; ``Pool.invoke()`` is the only piece that
talks to AWS, through the front's instance role (bedrock:InvokeModel only).

Why a POOL of models rather than one: on this account every Bedrock model has
a small, mostly non-adjustable "requests per minute" quota in eu-west-3
(measured 2026-09-24: Nova Micro/Lite/2 Lite 20, Nova Pro 25, Claude Haiku
4.5 10 adjustable, Mistral 7B 8, Pixtral Large 1). ~300 players need more
than any single model offers, so the gateway spreads the traffic: each model
carries its own per-minute budget, a team sticks to "its" model while that
model has room, and overflows to the next one. Tool-calling requests (two
challenges) only go to models that support tool use; verified in eu-west-3
with the four Nova models (no paperwork) and Claude Haiku 4.5 (after the
one-time Anthropic "use case details" form in the Bedrock console).

Pool syntax (AI_BEDROCK_MODELS / AI_BEDROCK_CHAT_MODELS):
    model_id[=requests_per_minute][,model_id[=rpm]...]
The rpm defaults to 10 when omitted. CHAT_MODELS are extra models used only
for requests WITHOUT tools (e.g. Mistral 7B, which cannot call tools).
"""

import os
import re
import threading
import time
import uuid
import zlib


class BedrockError(Exception):
    """A backend failure mapped to an HTTP status the gateway can return.

    ``busy`` means "retry later" (throttling, capacity): the gateway returns the
    same 503 shape as when the GPU queue is full. Otherwise it is a 502.
    """

    def __init__(self, message, busy=False):
        super().__init__(message)
        self.busy = busy


DEFAULT_POOL = (
    "eu.amazon.nova-lite-v1:0=20,"
    "eu.amazon.nova-micro-v1:0=20,"
    "eu.amazon.nova-pro-v1:0=25,"
    "eu.amazon.nova-2-lite-v1:0=20"
)

# Models that reject the Converse ``system`` parameter: the system prompt is
# folded into the first user turn instead (also done on the fly when Bedrock
# says so, for models not listed here).
_NO_SYSTEM_PREFIXES = ("mistral.mistral-7b", "mistral.mixtral-8x7b")

_THINKING = re.compile(r"<thinking>.*?</thinking>\s*", re.S)
_RESPONSE_TAGS = re.compile(r"</?response>", re.I)


def parse_pool(spec, default_rpm=10):
    """'a=20,b, c=5' -> [('a', 20), ('b', 10), ('c', 5)]. Blank -> []."""
    out = []
    for item in (spec or "").split(","):
        item = item.strip()
        if not item:
            continue
        name, _, rpm = item.partition("=")
        try:
            rpm_i = int(rpm) if rpm.strip() else default_rpm
        except ValueError:
            rpm_i = default_rpm
        out.append((name.strip(), max(1, rpm_i)))
    return out


def _new_tool_use_id():
    # Ollama tool calls carry no id: mint one per call, unique within a request.
    return "tooluse_" + uuid.uuid4().hex[:22]


def _text_blocks(content):
    """Bedrock rejects empty text blocks: emit none rather than ``{"text": ""}``."""
    if content is None:
        return []
    text = content if isinstance(content, str) else str(content)
    return [{"text": text}] if text.strip() else []


def supports_system(model_id):
    return not model_id.startswith(_NO_SYSTEM_PREFIXES)


def to_converse(payload, model_id, default_max_tokens=1024, system_inline=None):
    """Translate an Ollama ``/api/chat`` body into ``converse()`` kwargs.

    Handles the message shapes the challenges produce:
      * ``system`` messages -> the ``system`` parameter (concatenated), or
        prepended to the first user turn when the model has no system support
      * ``assistant`` messages with ``tool_calls`` -> ``toolUse`` blocks, with
        minted ids that the following ``tool`` messages consume in order
      * ``tool`` messages -> ``toolResult`` blocks inside a ``user`` turn
      * consecutive same-role turns are merged (Converse requires alternation)
      * ``tools`` (OpenAI/Ollama function schema) -> ``toolConfig``
      * ``options.temperature`` / ``num_predict`` / ``stop`` -> inferenceConfig
    """
    if system_inline is None:
        system_inline = not supports_system(model_id)
    system_parts = []
    messages = []
    pending_ids = []  # toolUse ids minted for the last assistant turn, FIFO

    def _append(role, blocks):
        if not blocks:
            return
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"].extend(blocks)
        else:
            messages.append({"role": role, "content": list(blocks)})

    for m in payload.get("messages") or []:
        role = (m.get("role") or "user").lower()
        content = m.get("content", "")
        if role == "system":
            if isinstance(content, str) and content.strip():
                system_parts.append(content)
            continue
        if role == "assistant":
            blocks = _text_blocks(content)
            pending_ids = []
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function", {}) or {}
                args = fn.get("arguments", {})
                if not isinstance(args, dict):
                    args = {"input": args}
                tid = _new_tool_use_id()
                pending_ids.append(tid)
                blocks.append(
                    {
                        "toolUse": {
                            "toolUseId": tid,
                            "name": fn.get("name", "") or "tool",
                            "input": args,
                        }
                    }
                )
            _append("assistant", blocks)
            continue
        if role == "tool":
            # A tool result answers the most recent unanswered toolUse. Without
            # a matching id Converse rejects the turn, so an orphan result is
            # downgraded to plain user text (keeps the conversation valid).
            text = content if isinstance(content, str) else str(content)
            if pending_ids:
                tid = pending_ids.pop(0)
                _append(
                    "user",
                    [
                        {
                            "toolResult": {
                                "toolUseId": tid,
                                "content": [{"text": text or "{}"}],
                                "status": "success",
                            }
                        }
                    ],
                )
            else:
                name = m.get("tool_name") or m.get("name") or "tool"
                _append("user", _text_blocks(f"[{name} result] {text}"))
            continue
        # user (or anything else): plain text
        _append("user", _text_blocks(content))

    # Converse requires the first turn to be a user turn.
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    if not messages:
        messages = [{"role": "user", "content": [{"text": "(empty)"}]}]

    kwargs = {"modelId": model_id, "messages": messages}
    if system_parts:
        system_text = "\n\n".join(system_parts)
        if system_inline:
            first = messages[0]["content"]
            if first and "text" in first[0]:
                first[0] = {"text": f"{system_text}\n\n{first[0]['text']}"}
            else:
                first.insert(0, {"text": system_text})
        else:
            kwargs["system"] = [{"text": system_text}]

    tools = payload.get("tools") or []
    specs = []
    for t in tools:
        fn = t.get("function", t) or {}
        name = fn.get("name")
        if not name:
            continue
        params = fn.get("parameters") or {"type": "object", "properties": {}}
        spec = {"name": name, "inputSchema": {"json": params}}
        if fn.get("description"):
            spec["description"] = fn["description"]
        specs.append({"toolSpec": spec})
    if specs:
        kwargs["toolConfig"] = {"tools": specs}

    opts = payload.get("options") or {}
    inf = {"maxTokens": int(opts.get("num_predict") or default_max_tokens)}
    if opts.get("temperature") is not None:
        inf["temperature"] = float(opts["temperature"])
    if opts.get("top_p") is not None:
        inf["topP"] = float(opts["top_p"])
    stop = opts.get("stop")
    if isinstance(stop, str):
        stop = [stop]
    if stop:
        inf["stopSequences"] = [str(s) for s in stop][:4]
    kwargs["inferenceConfig"] = inf
    return kwargs


def from_converse(resp, model_id, started=None):
    """Translate a ``converse()`` response into Ollama's ``/api/chat`` shape.

    Nova models narrate a ``<thinking>...</thinking>`` block before a tool
    call and sometimes wrap the final answer in ``<response>`` tags; Ollama
    models do not, and the challenges echo the text to the player, so both
    are stripped.
    """
    out = (resp.get("output") or {}).get("message") or {}
    texts, tool_calls = [], []
    for block in out.get("content") or []:
        if "text" in block:
            texts.append(_RESPONSE_TAGS.sub("", _THINKING.sub("", block["text"])))
        elif "toolUse" in block:
            tu = block["toolUse"]
            tool_calls.append(
                {
                    "function": {
                        "name": tu.get("name", ""),
                        "arguments": tu.get("input") or {},
                    }
                }
            )
    usage = resp.get("usage") or {}
    stop = resp.get("stopReason") or "end_turn"
    message = {"role": "assistant", "content": "".join(texts).strip()}
    if tool_calls:
        message["tool_calls"] = tool_calls
    data = {
        "model": model_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "message": message,
        "done": True,
        "done_reason": "tool_calls" if stop == "tool_use" else "stop",
        "prompt_eval_count": int(usage.get("inputTokens") or 0),
        "eval_count": int(usage.get("outputTokens") or 0),
    }
    if started is not None:
        data["total_duration"] = int((time.time() - started) * 1e9)
    return data


# --- model pool ------------------------------------------------------------

_BUSY_CODES = {
    "ThrottlingException",
    "ServiceUnavailableException",
    "ModelNotReadyException",
    "ModelTimeoutException",
    "InternalServerException",
    "ServiceQuotaExceededException",
}

THROTTLE_COOLDOWN = 20  # seconds a model sits out after Bedrock throttled it


class Pool:
    """Spreads requests over several models, each with its own requests-per-
    minute budget, mirroring the per-model Bedrock quotas.

    ``order(team, tools)`` is deterministic and pure so the choice is testable:
    the team's home model comes first (stable hash), then the rest in pool
    order; tool-calling requests never see chat-only models.
    """

    def __init__(
        self, models, chat_models=(), region=None, timeout=180, default_max_tokens=1024
    ):
        self.models = list(models)  # [(id, rpm)] tool-capable
        self.chat_models = list(chat_models)  # [(id, rpm)] chat only
        self.region = region or os.environ.get("AWS_REGION") or "eu-west-3"
        self.timeout = timeout
        self.default_max_tokens = default_max_tokens
        self._lock = threading.Lock()
        self._sent = {}  # model -> [ts, ...] within the last 60 s
        self._cooldown = {}  # model -> until ts
        self._client = None
        if not self.models and not self.chat_models:
            raise ValueError("pool vide: renseigner AI_BEDROCK_MODELS")

    # -- pure part ----------------------------------------------------------
    def order(self, team, tools):
        cands = list(self.models)
        if not tools:
            cands += self.chat_models
        if not cands:
            return []
        start = zlib.crc32(str(team).encode()) % len(cands)
        return cands[start:] + cands[:start]

    def listing(self):
        return [
            {"name": m, "model": m, "rpm": rpm, "tools": True} for m, rpm in self.models
        ] + [
            {"name": m, "model": m, "rpm": rpm, "tools": False}
            for m, rpm in self.chat_models
        ]

    # -- accounting -----------------------------------------------------------
    def _take_slot(self, model, rpm, now):
        with self._lock:
            if self._cooldown.get(model, 0) > now:
                return False
            sent = [t for t in self._sent.get(model, []) if t > now - 60]
            if len(sent) >= rpm:
                self._sent[model] = sent
                return False
            sent.append(now)
            self._sent[model] = sent
            return True

    def _give_back(self, model, now):
        with self._lock:
            sent = self._sent.get(model, [])
            if now in sent:
                sent.remove(now)

    def _throttled(self, model, now):
        with self._lock:
            self._cooldown[model] = now + THROTTLE_COOLDOWN

    def stats(self):
        now = time.time()
        with self._lock:
            return {
                m: {
                    "rpm": rpm,
                    "last_minute": len(
                        [t for t in self._sent.get(m, []) if t > now - 60]
                    ),
                    "cooldown": max(0, int(self._cooldown.get(m, 0) - now)),
                }
                for m, rpm in self.models + self.chat_models
            }

    # -- live call ------------------------------------------------------------
    def _get_client(self):
        if self._client is None:
            import boto3
            from botocore.config import Config

            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                config=Config(
                    read_timeout=self.timeout,
                    connect_timeout=10,
                    # No SDK retries: a throttle must fall through to the
                    # next model at once, not burn 2 x backoff on the same one.
                    retries={"max_attempts": 1, "mode": "standard"},
                ),
            )
        return self._client

    def _converse(self, payload, model):
        kwargs = to_converse(payload, model, self.default_max_tokens)
        try:
            return self._get_client().converse(**kwargs)
        except Exception as e:  # ClientError: retry once with inline system
            code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
            msg = getattr(e, "response", {}).get("Error", {}).get("Message", "")
            if (
                code == "ValidationException"
                and "system" in msg.lower()
                and "system" in kwargs
            ):
                kwargs = to_converse(
                    payload, model, self.default_max_tokens, system_inline=True
                )
                return self._get_client().converse(**kwargs)
            raise

    def invoke(self, payload, team=""):
        """Run one Ollama-shaped chat request. Returns the Ollama-shaped reply
        (with ``model`` = the Bedrock model that answered) or raises
        BedrockError."""
        from botocore.exceptions import BotoCoreError, ClientError

        tools = bool(payload.get("tools"))
        last_err = None
        for model, rpm in self.order(team, tools):
            now = time.time()
            if not self._take_slot(model, rpm, now):
                continue
            started = time.time()
            try:
                resp = self._converse(payload, model)
            except ClientError as e:
                code = (e.response.get("Error") or {}).get("Code", "")
                msg = (e.response.get("Error") or {}).get("Message", "")
                last_err = BedrockError(
                    f"{model}: {code}: {msg[:200]}", busy=code in _BUSY_CODES
                )
                if code in _BUSY_CODES:
                    self._throttled(model, now)
                    continue  # next model in the team's order
                self._give_back(model, now)
                raise last_err
            except BotoCoreError as e:
                # Connection/read timeouts, credential lookups...
                last_err = BedrockError(f"{model}: {e.__class__.__name__}", busy=True)
                self._throttled(model, now)
                continue
            return from_converse(resp, model, started)
        if last_err is None:
            last_err = BedrockError(
                "tous les modeles du pool sont a leur quota", busy=True
            )
        raise last_err
