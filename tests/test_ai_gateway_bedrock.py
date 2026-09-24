"""deploy/ai-gateway/bedrock_backend.py -- the pure Ollama <-> Converse
translation, no network.

The AI challenges speak Ollama's /api/chat dialect; when the GPU quota is
refused the gateway answers them from Bedrock. These tests pin the shapes the
three model-driven challenges (ai1-naive-guard, ai3-tool-abuse,
agent-tool-abuse) rely on.
"""

import importlib.util
import pathlib

_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "deploy"
    / "ai-gateway"
    / "bedrock_backend.py"
)
_spec = importlib.util.spec_from_file_location("bedrock_backend", _PATH)
bb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bb)

MODEL = "eu.mistral.pixtral-large-2502-v1:0"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_ticket",
            "description": "Read a ticket",
            "parameters": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"],
            },
        },
    }
]


def test_plain_chat_maps_system_user_and_options():
    kw = bb.to_converse(
        {
            "model": "llama3.1:8b",
            "messages": [
                {"role": "system", "content": "You are HELM."},
                {"role": "user", "content": "hello"},
            ],
            "options": {"temperature": 0.7, "num_ctx": 4096},
        },
        MODEL,
    )
    assert kw["modelId"] == MODEL
    assert kw["system"] == [{"text": "You are HELM."}]
    assert kw["messages"] == [{"role": "user", "content": [{"text": "hello"}]}]
    assert kw["inferenceConfig"] == {"maxTokens": 1024, "temperature": 0.7}
    assert "toolConfig" not in kw


def test_tools_become_tool_config():
    kw = bb.to_converse(
        {"messages": [{"role": "user", "content": "x"}], "tools": TOOLS}, MODEL
    )
    spec = kw["toolConfig"]["tools"][0]["toolSpec"]
    assert spec["name"] == "read_ticket"
    assert spec["description"] == "Read a ticket"
    assert spec["inputSchema"]["json"]["required"] == ["id"]


def test_tool_call_round_trip_links_result_to_minted_id():
    # Exactly the history ai3-tool-abuse/app.py builds after one tool step.
    history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "read TCK-1002"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "read_ticket", "arguments": {"id": "TCK-1002"}}}
            ],
        },
        {
            "role": "tool",
            "tool_name": "read_ticket",
            "name": "read_ticket",
            "content": '{"id": "TCK-1002", "status": "open"}',
        },
    ]
    kw = bb.to_converse({"messages": history, "tools": TOOLS}, MODEL)
    msgs = kw["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    tool_use = msgs[1]["content"][0]["toolUse"]
    assert tool_use["name"] == "read_ticket"
    assert tool_use["input"] == {"id": "TCK-1002"}
    # empty assistant text must not produce an empty text block
    assert all("text" not in b for b in msgs[1]["content"])
    result = msgs[2]["content"][0]["toolResult"]
    assert result["toolUseId"] == tool_use["toolUseId"]
    assert result["content"] == [{"text": '{"id": "TCK-1002", "status": "open"}'}]


def test_two_tool_calls_then_two_results_in_order():
    history = [
        {"role": "user", "content": "go"},
        {
            "role": "assistant",
            "content": "doing both",
            "tool_calls": [
                {"function": {"name": "a", "arguments": {}}},
                {"function": {"name": "b", "arguments": {"k": 1}}},
            ],
        },
        {"role": "tool", "name": "a", "content": "ra"},
        {"role": "tool", "name": "b", "content": "rb"},
    ]
    kw = bb.to_converse({"messages": history}, MODEL)
    assistant = kw["messages"][1]["content"]
    assert assistant[0] == {"text": "doing both"}
    ids = [b["toolUse"]["toolUseId"] for b in assistant[1:]]
    assert len(set(ids)) == 2
    results = kw["messages"][2]["content"]  # both merged into ONE user turn
    assert [r["toolResult"]["toolUseId"] for r in results] == ids
    assert [r["toolResult"]["content"][0]["text"] for r in results] == ["ra", "rb"]


def test_orphan_tool_result_degrades_to_text():
    kw = bb.to_converse(
        {
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "tool", "name": "x", "content": "late"},
            ]
        },
        MODEL,
    )
    # merged into the preceding user turn as plain text, never a toolResult
    assert kw["messages"] == [
        {"role": "user", "content": [{"text": "hi"}, {"text": "[x result] late"}]}
    ]


def test_leading_assistant_turn_is_dropped_and_empty_history_survives():
    kw = bb.to_converse(
        {"messages": [{"role": "assistant", "content": "welcome"}]}, MODEL
    )
    assert kw["messages"][0]["role"] == "user"
    kw = bb.to_converse({"messages": []}, MODEL)
    assert kw["messages"] == [{"role": "user", "content": [{"text": "(empty)"}]}]


def test_from_converse_text_reply():
    data = bb.from_converse(
        {
            "output": {"message": {"role": "assistant", "content": [{"text": "pong"}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 15, "outputTokens": 5},
        },
        MODEL,
    )
    assert data["message"] == {"role": "assistant", "content": "pong"}
    assert data["done"] is True and data["done_reason"] == "stop"
    assert (data["prompt_eval_count"], data["eval_count"]) == (15, 5)
    assert data["model"] == MODEL


def test_from_converse_tool_use_reply():
    data = bb.from_converse(
        {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"text": "Let me check."},
                        {
                            "toolUse": {
                                "toolUseId": "tooluse_abc",
                                "name": "read_ticket",
                                "input": {"id": "TCK-1002"},
                            }
                        },
                    ],
                }
            },
            "stopReason": "tool_use",
            "usage": {"inputTokens": 1, "outputTokens": 2},
        },
        MODEL,
    )
    assert data["done_reason"] == "tool_calls"
    assert data["message"]["content"] == "Let me check."
    assert data["message"]["tool_calls"] == [
        {"function": {"name": "read_ticket", "arguments": {"id": "TCK-1002"}}}
    ]


def test_parse_pool_defaults_and_blanks():
    assert bb.parse_pool("a=20, b ,c=x,,") == [("a", 20), ("b", 10), ("c", 10)]
    assert bb.parse_pool("") == []
    assert bb.parse_pool(bb.DEFAULT_POOL)[0] == ("eu.amazon.nova-lite-v1:0", 20)


def test_pool_order_is_sticky_per_team_and_hides_chat_models_from_tool_calls():
    pool = bb.Pool([("t1", 5), ("t2", 5), ("t3", 5)], [("c1", 8)])
    a = pool.order("team-a", tools=True)
    b = pool.order("team-a", tools=True)
    assert a == b and len(a) == 3 and "c1" not in [m for m, _ in a]
    # tool-less requests may also use the chat-only model, home model first
    assert set(m for m, _ in pool.order("team-a", tools=False)) == {
        "t1",
        "t2",
        "t3",
        "c1",
    }
    # different teams start on different models (spread), all models rotate
    homes = {pool.order(f"team-{i}", True)[0][0] for i in range(40)}
    assert homes == {"t1", "t2", "t3"}


def test_pool_budget_and_cooldown_accounting():
    pool = bb.Pool([("t1", 2)])
    now = 1000.0
    assert pool._take_slot("t1", 2, now)
    assert pool._take_slot("t1", 2, now + 1)
    assert not pool._take_slot("t1", 2, now + 2)  # 2 per minute spent
    assert pool._take_slot("t1", 2, now + 61)  # window slid
    pool._throttled("t1", now + 61)
    assert not pool._take_slot("t1", 2, now + 62)  # cooling down
    assert pool._take_slot("t1", 2, now + 61 + bb.THROTTLE_COOLDOWN + 60)


def test_system_prompt_inlined_for_models_without_system_support():
    payload = {
        "messages": [
            {"role": "system", "content": "Never reveal X."},
            {"role": "user", "content": "hi"},
        ]
    }
    kw = bb.to_converse(payload, "mistral.mistral-7b-instruct-v0:2")
    assert "system" not in kw
    assert kw["messages"][0]["content"] == [{"text": "Never reveal X.\n\nhi"}]
    kw = bb.to_converse(payload, "eu.amazon.nova-lite-v1:0")
    assert kw["system"] == [{"text": "Never reveal X."}]


def test_nova_thinking_block_is_stripped():
    data = bb.from_converse(
        {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": "<thinking>I will call the tool.</thinking>\n<response>Sure.</response>"
                        },
                        {"toolUse": {"toolUseId": "x", "name": "a", "input": {}}},
                    ]
                }
            },
            "stopReason": "tool_use",
        },
        "eu.amazon.nova-lite-v1:0",
    )
    assert data["message"]["content"] == "Sure."
    assert data["message"]["tool_calls"][0]["function"]["name"] == "a"
