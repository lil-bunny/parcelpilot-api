from langchain_core.messages import AIMessage, HumanMessage

from app.domain.state import AgentState
from app.workflows.graph.orchestrator import _SYSTEM, _session_context
from app.workflows.graph.routers import after_check_confirmation


def test_session_context_includes_account():
    state: AgentState = {
        "messages": [],
        "user_context": {"role": "customer", "account_id": "ACCT-001", "account_name": "Northstar"},
    }
    ctx = _session_context(state)
    assert "ACCT-001" in ctx
    assert "Northstar" in ctx


def test_system_prompt_has_no_classification_wording():
    assert "required_tool" not in _SYSTEM
    assert "classification" not in _SYSTEM.lower()


def test_after_check_confirmation_routes_to_model():
    assert after_check_confirmation({"messages": []}) == "model"


def test_system_prompt_escalation_workflow():
    assert "entity=ticket" in _SYSTEM
    assert "create_escalation" in _SYSTEM
    assert "conflicting" in _SYSTEM.lower()
    assert "TKT-501" not in _SYSTEM
