from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool
from typing_extensions import Annotated

from app.integrations.db.postgres import execute, fetch_one
from app.services.operational_data import UnauthorizedError, _require_customer_account
from langgraph.prebuilt import InjectedState

ACTION_TOOLS = frozenset({"create_escalation", "update_ticket", "create_followup"})


def _auth_ticket(ticket_id: str, user_context: dict[str, Any]) -> dict:
    row = fetch_one("SELECT * FROM tickets WHERE ticket_id = %s", (ticket_id,))
    if row is None:
        raise ValueError(f"Ticket {ticket_id} not found")
    if user_context.get("role") == "customer":
        auth = _require_customer_account(user_context)
        if row["account_id"] != auth:
            raise UnauthorizedError("Not authorized for this ticket")
    return row


def escalate_ticket(ticket_id: str, reason: str, user_context: dict[str, Any]) -> dict:
    _auth_ticket(ticket_id, user_context)
    execute(
        "UPDATE tickets SET status = %s, description = COALESCE(description, '') || %s WHERE ticket_id = %s",
        ("escalated", f"\n[escalation] {reason}", ticket_id),
    )
    return {"ok": True, "ticket_id": ticket_id, "status": "escalated"}


def update_ticket_row(
    ticket_id: str, status: str, note: str, user_context: dict[str, Any]
) -> dict:
    _auth_ticket(ticket_id, user_context)
    execute(
        "UPDATE tickets SET status = %s, description = COALESCE(description, '') || %s WHERE ticket_id = %s",
        (status, f"\n[update] {note}", ticket_id),
    )
    return {"ok": True, "ticket_id": ticket_id, "status": status}


def add_followup(ticket_id: str, message: str, user_context: dict[str, Any]) -> dict:
    _auth_ticket(ticket_id, user_context)
    execute(
        "UPDATE tickets SET description = COALESCE(description, '') || %s, last_customer_message_at = NOW() WHERE ticket_id = %s",
        (f"\n[followup] {message}", ticket_id),
    )
    return {"ok": True, "ticket_id": ticket_id}


@tool
def create_escalation(ticket_id: str, reason: str, state: Annotated[dict, InjectedState]) -> str:
    """Create an escalation on a support ticket.

    Look up the ticket with query_operational_data first. Derive reason from ticket
    subject/description when possible. Call this to propose the action — the workflow
    asks the user for explicit confirmation before the DB write (may be mocked in tests).
    """
    user_context = state.get("user_context") or {}
    if not state.get("confirmation_received"):
        return json.dumps({"error": "confirmation_required", "message": "User must confirm before escalation."})
    try:
        return json.dumps(escalate_ticket(ticket_id, reason, user_context))
    except (UnauthorizedError, ValueError) as exc:
        return json.dumps({"error": str(exc)})


@tool
def update_ticket(
    ticket_id: str,
    status: str,
    note: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """Update ticket status. Requires explicit user confirmation before this runs."""
    user_context = state.get("user_context") or {}
    if not state.get("confirmation_received"):
        return json.dumps({"error": "confirmation_required"})
    try:
        return json.dumps(update_ticket_row(ticket_id, status, note, user_context))
    except (UnauthorizedError, ValueError) as exc:
        return json.dumps({"error": str(exc)})


@tool
def create_followup(
    ticket_id: str,
    message: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """Record a follow-up note on a ticket. Requires explicit user confirmation before this runs."""
    user_context = state.get("user_context") or {}
    if not state.get("confirmation_received"):
        return json.dumps({"error": "confirmation_required"})
    try:
        return json.dumps(add_followup(ticket_id, message, user_context))
    except (UnauthorizedError, ValueError) as exc:
        return json.dumps({"error": str(exc)})


def run_action(name: str, args: dict[str, Any], user_context: dict[str, Any]) -> str:
    """Execute a confirmed action outside the tool node."""
    if name == "create_escalation":
        return json.dumps(escalate_ticket(args["ticket_id"], args["reason"], user_context))
    if name == "update_ticket":
        return json.dumps(update_ticket_row(args["ticket_id"], args["status"], args["note"], user_context))
    if name == "create_followup":
        return json.dumps(add_followup(args["ticket_id"], args["message"], user_context))
    raise ValueError(f"Unknown action: {name}")
