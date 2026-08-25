from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage


def _trace_messages(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    """Build ordered tool call rows from a slice of the conversation."""
    pending: dict[str, dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []
    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            call_id = call.get("id") or str(len(ordered))
            row = {
                "id": call_id,
                "name": call.get("name"),
                "args": call.get("args") or {},
                "ok": True,
                "result": None,
            }
            pending[call_id] = row
            ordered.append(row)
        if isinstance(message, ToolMessage):
            row = pending.get(message.tool_call_id)
            if row is None:
                continue
            row["result"] = message.content if isinstance(message.content, str) else str(message.content)
            status = getattr(message, "status", None)
            if status == "error":
                row["ok"] = False
            elif isinstance(message.content, str) and message.content.startswith("Error"):
                row["ok"] = False
    return ordered


def _index_last_user_message(messages: list[BaseMessage]) -> int:
    last = 0
    for i, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            last = i
        elif isinstance(message, dict) and message.get("role") == "user":
            last = i
    return last


def tool_trace_from_messages(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    """All tool calls in the thread (debug / full history)."""
    return _trace_messages(messages)


def tool_trace_since_last_user_message(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    """Tool calls for the current turn only — avoids stale PDF sources from prior turns."""
    start = _index_last_user_message(messages)
    return _trace_messages(messages[start:])
