import importlib
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.services.orchestrator_service import reset_graph
from app.tools.trace import tool_trace_since_last_user_message
from app.workflows.compiler.compiler import compile_orchestrator
from app.workflows.graph.routers import after_check_confirmation

TKT_501_JSON = (
    '{"found": true, "data": {"ticket_id": "TKT-501", "subject": "All shipment creation is failing", '
    '"description": "Every user at Northstar gets HTTP 500 when creating any shipment.", "status": "open"}}'
)


def _fake_ticket_lookup(entity, filters, user_context):
    import json

    if entity == "ticket" and filters.get("ticket_id") == "TKT-501":
        return TKT_501_JSON
    return json.dumps({"found": False})


def _escalation_mock_model(extra=None):
    responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "query_operational_data",
                    "args": {"entity": "ticket", "filters": {"ticket_id": "TKT-501"}},
                    "id": "c1",
                    "type": "tool_call",
                }
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "create_escalation",
                    "args": {
                        "ticket_id": "TKT-501",
                        "reason": "All shipment creation is failing",
                    },
                    "id": "c2",
                    "type": "tool_call",
                }
            ],
        ),
    ]
    if extra:
        responses.extend(extra)
    return _MockModel(responses)


def _patch_ticket_lookup(monkeypatch):
    mod = importlib.import_module("app.tools.definitions.query_operational_data")
    monkeypatch.setattr(mod, "query_json", _fake_ticket_lookup)


def _prepare_escalation_graph(monkeypatch, thread_id="esc-flow"):
    _patch_ticket_lookup(monkeypatch)
    reset_graph()
    graph = compile_orchestrator(_escalation_mock_model())
    cfg = {"configurable": {"thread_id": thread_id}}
    out = graph.invoke(
        {"messages": [HumanMessage(content="I want to escalate TKT-501.")], "user_context": ACCT_001},
        config=cfg,
    )
    return graph, cfg, out


class _MockModel:
    def __init__(self, responses: list):
        self._responses = list(responses)

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        if not self._responses:
            raise RuntimeError("mock model out of responses")
        return self._responses.pop(0)


ACCT_001 = {"role": "customer", "account_id": "ACCT-001", "account_name": "Northstar"}


def test_check_confirmation_routes_to_model():
    assert after_check_confirmation({"messages": []}) == "model"


def test_graph_text_reply_no_tools():
    reset_graph()
    model = _MockModel([AIMessage(content="Hi! How can I help with your shipments?")])
    graph = compile_orchestrator(model)
    out = graph.invoke(
        {"messages": [HumanMessage(content="hello")], "user_context": ACCT_001},
        config={"configurable": {"thread_id": "t1"}},
    )
    assert out["messages"][-1].content.startswith("Hi!")
    assert tool_trace_since_last_user_message(out["messages"]) == []


def test_graph_runs_echo_tool():
    reset_graph()
    model = _MockModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "echo", "args": {"text": "hi"}, "id": "c1", "type": "tool_call"},
                ],
            ),
            AIMessage(content="Done."),
        ]
    )
    graph = compile_orchestrator(model)
    out = graph.invoke(
        {"messages": [HumanMessage(content="echo hi")], "user_context": ACCT_001},
        config={"configurable": {"thread_id": "t2"}},
    )
    trace = tool_trace_since_last_user_message(out["messages"])
    assert any(t["name"] == "echo" for t in trace)
    assert out["messages"][-1].content == "Done."


def test_graph_escalation_requires_confirmation():
    reset_graph()
    model = _MockModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_escalation",
                        "args": {"ticket_id": "T-1001", "reason": "late"},
                        "id": "c1",
                        "type": "tool_call",
                    }
                ],
            ),
        ]
    )
    graph = compile_orchestrator(model)
    out = graph.invoke(
        {"messages": [HumanMessage(content="escalate ticket")], "user_context": ACCT_001},
        config={"configurable": {"thread_id": "t3"}},
    )
    assert out.get("confirmation_required") is True
    assert out.get("proposed_action", {}).get("name") == "create_escalation"
    trace = tool_trace_since_last_user_message(out["messages"])
    esc = next(t for t in trace if t["name"] == "create_escalation")
    assert "pending_confirmation" in (esc["result"] or "")
    assert "yes" in out["messages"][-1].content.lower()


def test_checkpoint_accumulates_messages():
    reset_graph()
    model = _MockModel(
        [
            AIMessage(content="You have 2 orders."),
            AIMessage(content="Our SLA is 30 minutes for critical issues."),
        ]
    )
    graph = compile_orchestrator(model)
    cfg = {"configurable": {"thread_id": "t4"}}
    graph.invoke(
        {"messages": [HumanMessage(content="list orders")], "user_context": ACCT_001},
        config=cfg,
    )
    out = graph.invoke(
        {"messages": [HumanMessage(content="tell me about SLA")], "user_context": ACCT_001},
        config=cfg,
    )
    user_lines = [m.content for m in out["messages"] if isinstance(m, HumanMessage)]
    assert user_lines == ["list orders", "tell me about SLA"]


def test_escalation_prepare_asks_confirmation(monkeypatch):
    graph, cfg, out = _prepare_escalation_graph(monkeypatch)
    assert out.get("confirmation_required") is True
    proposed = out.get("proposed_action") or {}
    assert proposed.get("name") == "create_escalation"
    assert proposed.get("args", {}).get("ticket_id") == "TKT-501"
    trace = tool_trace_since_last_user_message(out["messages"])
    esc = next(t for t in trace if t["name"] == "create_escalation")
    assert "pending_confirmation" in (esc["result"] or "")
    last = out["messages"][-1].content.lower()
    assert "yes" in last
    assert "tkt-501" in last
    assert "will proceed" not in last


def test_escalation_confirm_executes(monkeypatch):
    graph, cfg, _prepare = _prepare_escalation_graph(monkeypatch)
    with patch("app.workflows.graph.confirmation.run_action") as mock_run:
        mock_run.return_value = '{"ok": true, "ticket_id": "TKT-501", "status": "escalated"}'
        out = graph.invoke(
            {"messages": [HumanMessage(content="Yes, proceed.")], "user_context": ACCT_001},
            config=cfg,
        )
        mock_run.assert_called_once()
        args = mock_run.call_args[0]
        assert args[0] == "create_escalation"
        assert args[1]["ticket_id"] == "TKT-501"
    assert "escalated" in out["messages"][-1].content.lower()


def test_escalation_reject_does_not_execute(monkeypatch):
    _patch_ticket_lookup(monkeypatch)
    reset_graph()
    graph = compile_orchestrator(
        _escalation_mock_model(extra=[AIMessage(content="Let me know if you need anything else.")])
    )
    cfg = {"configurable": {"thread_id": "esc-reject"}}
    graph.invoke(
        {"messages": [HumanMessage(content="I want to escalate TKT-501.")], "user_context": ACCT_001},
        config=cfg,
    )
    with patch("app.workflows.graph.confirmation.run_action") as mock_run:
        out = graph.invoke(
            {"messages": [HumanMessage(content="No, don't do it.")], "user_context": ACCT_001},
            config=cfg,
        )
        mock_run.assert_not_called()
    assert out.get("proposed_action") is None
    assert out.get("confirmation_required") is False


def test_escalation_ambiguous_does_not_execute(monkeypatch):
    _patch_ticket_lookup(monkeypatch)
    reset_graph()
    graph = compile_orchestrator(
        _escalation_mock_model(
            extra=[AIMessage(content="Please reply yes or no to confirm the escalation.")]
        )
    )
    cfg = {"configurable": {"thread_id": "esc-ambiguous"}}
    graph.invoke(
        {"messages": [HumanMessage(content="I want to escalate TKT-501.")], "user_context": ACCT_001},
        config=cfg,
    )
    with patch("app.workflows.graph.confirmation.run_action") as mock_run:
        out = graph.invoke(
            {"messages": [HumanMessage(content="Maybe.")], "user_context": ACCT_001},
            config=cfg,
        )
        mock_run.assert_not_called()
    assert out.get("confirmation_required") is True
    assert out.get("proposed_action") is not None


def _tool_calls_have_responses(messages: list) -> bool:
    for i, message in enumerate(messages):
        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            continue
        ids = {tc.get("id") for tc in tool_calls if tc.get("id")}
        answered = {
            m.tool_call_id
            for m in messages[i + 1 : i + 1 + len(tool_calls) + 2]
            if isinstance(m, ToolMessage)
        }
        if not ids <= answered:
            return False
    return True


def test_thread_continues_after_escalation_gate(monkeypatch):
    _patch_ticket_lookup(monkeypatch)
    reset_graph()
    graph = compile_orchestrator(
        _escalation_mock_model(extra=[AIMessage(content="TKT-504 is still open.")])
    )
    cfg = {"configurable": {"thread_id": "thread-continuity"}}
    out = graph.invoke(
        {"messages": [HumanMessage(content="I want to escalate TKT-501.")], "user_context": ACCT_001},
        config=cfg,
    )
    assert _tool_calls_have_responses(out["messages"])
    with patch("app.workflows.graph.confirmation.run_action") as mock_run:
        mock_run.return_value = '{"ok": true, "ticket_id": "TKT-501", "status": "escalated"}'
        out2 = graph.invoke(
            {"messages": [HumanMessage(content="Yes, proceed.")], "user_context": ACCT_001},
            config=cfg,
        )
        mock_run.assert_called_once()
    assert _tool_calls_have_responses(out2["messages"])
    out3 = graph.invoke(
        {"messages": [HumanMessage(content="What about TKT-504?")], "user_context": ACCT_001},
        config=cfg,
    )
    assert out3["messages"][-1].content.startswith("TKT-504")
