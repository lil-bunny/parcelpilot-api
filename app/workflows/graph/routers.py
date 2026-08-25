from typing import Literal

from langgraph.graph import END

from app.domain.state import AgentState
from app.tools.definitions.actions import ACTION_TOOLS


def route_after_model(state: AgentState) -> Literal["tools", "request_confirmation", "__end__"]:
    messages = state["messages"]
    last = messages[-1]
    tool_calls = getattr(last, "tool_calls", None) or []
    if not tool_calls:
        return END
    if any(c.get("name") in ACTION_TOOLS for c in tool_calls) and not state.get("confirmation_received"):
        return "request_confirmation"
    return "tools"


def after_check_confirmation(state: AgentState) -> Literal["execute_action", "model"]:
    if state.get("confirmation_received") and state.get("proposed_action"):
        return "execute_action"
    return "model"
