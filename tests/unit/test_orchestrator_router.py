from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END

from app.workflows.graph.routers import route_after_model


def test_route_after_model_goes_to_tools_for_non_action_tools():
    state = {
        "messages": [
            HumanMessage(content="echo hi"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "echo",
                        "args": {"text": "hi"},
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            ),
        ]
    }
    assert route_after_model(state) == "tools"


def test_route_after_model_ends_when_model_answers():
    state = {"messages": [AIMessage(content="hello")]}
    assert route_after_model(state) == END


def test_route_after_model_requests_confirmation_for_action_tools():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_escalation",
                        "args": {"ticket_id": "T-1", "reason": "late"},
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            )
        ],
        "confirmation_received": False,
    }
    assert route_after_model(state) == "request_confirmation"
