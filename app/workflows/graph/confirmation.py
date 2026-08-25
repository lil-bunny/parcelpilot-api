import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.domain.confirmation import is_explicit_no, is_explicit_yes
from app.domain.state import AgentState
from app.tools.definitions.actions import ACTION_TOOLS, run_action


def _last_human_text(state: AgentState) -> str:
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            content = message.content
            return content if isinstance(content, str) else str(content)
        if isinstance(message, dict) and message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def check_confirmation_node(state: AgentState) -> dict:
    if not state.get("confirmation_required") or not state.get("proposed_action"):
        return {}
    text = _last_human_text(state).strip()
    if is_explicit_yes(text):
        return {"confirmation_received": True, "confirmation_required": False}
    if is_explicit_no(text):
        return {
            "confirmation_required": False,
            "confirmation_received": False,
            "proposed_action": None,
            "messages": [AIMessage(content="Okay, I won't proceed with that action.")],
        }
    return {}


def _confirmation_message(name: str, args: dict) -> str:
    if name == "create_escalation":
        ticket_id = args.get("ticket_id", "")
        reason = args.get("reason", "")
        return (
            f"I can escalate ticket {ticket_id} with reason: \"{reason}\". "
            "Reply **yes** to confirm or **no** to cancel."
        )
    return (
        f"I can run {name}({args}). "
        "This changes your ticket. Reply **yes** to confirm or **no** to cancel."
    )


def request_confirmation_node(state: AgentState) -> dict:
    last = state["messages"][-1]
    tool_calls = getattr(last, "tool_calls", None) or []
    call = next(c for c in tool_calls if c.get("name") in ACTION_TOOLS)
    args = call.get("args") or {}
    name = call.get("name")
    # ponytail: OpenAI requires a ToolMessage per tool_call_id when confirmation skips ToolNode
    tool_messages = [
        ToolMessage(
            content=json.dumps(
                {
                    "status": "pending_confirmation",
                    "message": "Awaiting explicit user confirmation before this action runs.",
                }
            ),
            tool_call_id=tc.get("id") or "",
        )
        for tc in tool_calls
    ]
    return {
        "proposed_action": {"name": name, "args": args},
        "confirmation_required": True,
        "confirmation_received": False,
        "messages": [*tool_messages, AIMessage(content=_confirmation_message(name, args))],
    }


def execute_action_node(state: AgentState) -> dict:
    action = state.get("proposed_action") or {}
    user_context = state.get("user_context") or {}
    try:
        result = run_action(action["name"], action.get("args") or {}, user_context)
    except Exception as exc:
        result = f'{{"error": "{exc}"}}'
    return {
        "proposed_action": None,
        "confirmation_received": False,
        "messages": [AIMessage(content=f"Action completed: {result}")],
    }
