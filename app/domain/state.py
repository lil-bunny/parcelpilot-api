from typing import Annotated, NotRequired

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """LangGraph MessagesState-style contract. Do not store secrets here."""

    messages: Annotated[list, add_messages]
    user_context: NotRequired[dict]
    proposed_action: NotRequired[dict | None]
    confirmation_required: NotRequired[bool]
    confirmation_received: NotRequired[bool]
    evidence: NotRequired[list]
    conflicts: NotRequired[list]
    confidence: NotRequired[float | None]
