from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.tools.trace import tool_trace_from_messages, tool_trace_since_last_user_message


def test_trace_lists_tools_in_order_with_results():
    messages = [
        HumanMessage(content="echo hi then ping"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "echo", "args": {"text": "hi"}, "id": "c1", "type": "tool_call"},
                {"name": "ping", "args": {}, "id": "c2", "type": "tool_call"},
            ],
        ),
        ToolMessage(content="hi", tool_call_id="c1"),
        ToolMessage(content="ok", tool_call_id="c2"),
        AIMessage(content="echoed hi and pinged"),
    ]
    trace = tool_trace_from_messages(messages)
    assert [t["name"] for t in trace] == ["echo", "ping"]
    assert trace[0]["args"] == {"text": "hi"}
    assert trace[0]["result"] == "hi"
    assert trace[0]["ok"] is True
    assert trace[1]["result"] == "ok"


def test_trace_since_last_user_excludes_prior_turn_tools():
    messages = [
        HumanMessage(content="cancel ORD-1001"),
        AIMessage(content="", tool_calls=[{"name": "get_applicable_rules", "args": {}, "id": "a1", "type": "tool_call"}]),
        ToolMessage(content="{}", tool_call_id="a1"),
        AIMessage(content="You can cancel for free."),
        HumanMessage(content="What plan am I on?"),
        AIMessage(content="", tool_calls=[{"name": "query_operational_data", "args": {}, "id": "b1", "type": "tool_call"}]),
        ToolMessage(content='{"found": true}', tool_call_id="b1"),
        AIMessage(content="Enterprise plan."),
    ]
    trace = tool_trace_since_last_user_message(messages)
    assert [t["name"] for t in trace] == ["query_operational_data"]
