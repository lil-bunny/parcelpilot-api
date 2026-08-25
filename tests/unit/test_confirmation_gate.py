from langchain_core.messages import AIMessage, ToolMessage

from app.domain.confirmation import is_explicit_no, is_explicit_yes
from app.domain.evidence import resolve_evidence
from app.workflows.graph.confirmation import request_confirmation_node
from app.workflows.graph.routers import route_after_model


def test_explicit_yes_no():
    assert is_explicit_yes("yes")
    assert is_explicit_yes("Go ahead")
    assert is_explicit_yes("Yes, proceed.")
    assert is_explicit_no("no")
    assert is_explicit_no("cancel")
    assert is_explicit_no("No, don't do it.")
    assert not is_explicit_yes("maybe")


def test_action_tool_blocked_without_confirmation():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_escalation",
                        "args": {"ticket_id": "T-1", "reason": "test"},
                        "id": "c1",
                        "type": "tool_call",
                    }
                ],
            )
        ],
        "confirmation_received": False,
    }
    assert route_after_model(state) == "request_confirmation"


def test_request_confirmation_sets_proposed_action():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_escalation",
                        "args": {"ticket_id": "T-1", "reason": "test"},
                        "id": "c1",
                        "type": "tool_call",
                    }
                ],
            )
        ]
    }
    out = request_confirmation_node(state)
    assert out["confirmation_required"] is True
    assert out["proposed_action"]["name"] == "create_escalation"


def test_request_confirmation_human_message():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_escalation",
                        "args": {"ticket_id": "TKT-501", "reason": "Shipment creation failing"},
                        "id": "c1",
                        "type": "tool_call",
                    }
                ],
            )
        ]
    }
    out = request_confirmation_node(state)
    msg = out["messages"][-1].content
    assert "TKT-501" in msg
    assert "Shipment creation failing" in msg
    assert "yes" in msg.lower()
    assert "create_escalation(" not in msg


def test_request_confirmation_adds_tool_messages():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_escalation",
                        "args": {"ticket_id": "TKT-501", "reason": "test"},
                        "id": "call_abc",
                        "type": "tool_call",
                    }
                ],
            )
        ]
    }
    out = request_confirmation_node(state)
    assert isinstance(out["messages"][0], ToolMessage)
    assert out["messages"][0].tool_call_id == "call_abc"
    assert "pending_confirmation" in out["messages"][0].content
    assert isinstance(out["messages"][-1], AIMessage)


def test_agreement_precedence_conflict_note():
    docs = [
        {"document_type": "northstar_agreement", "customer_id": "northstar", "authority": 4, "status": "current"},
        {"document_type": "support_policy", "customer_id": None, "authority": 2, "status": "current"},
    ]
    resolved = resolve_evidence([], docs)
    assert resolved["conflicts"]
    assert resolved["evidence"][0]["document_type"] == "northstar_agreement"
