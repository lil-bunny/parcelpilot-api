# state.data / AgentState keys the graph may read/write
AGENT_STATE_KEYS = {
    "messages": "LangGraph message list (add_messages reducer)",
    "user_context": "authenticated account context for system prompt and tool auth",
    "confirmation_required": "true when a write action awaits user yes/no",
    "proposed_action": "pending create_escalation / update_ticket / create_followup",
}
