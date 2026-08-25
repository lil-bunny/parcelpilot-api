from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from typing_extensions import Annotated

from app.services.operational_data import query_json
from langgraph.prebuilt import InjectedState


@tool
def query_operational_data(
    entity: str,
    filters: dict,
    state: Annotated[dict, InjectedState],
) -> str:
    """Fetch structured facts from PostgreSQL (accounts, orders, tickets).

    Use FIRST for plan, CSM, account_name, premium_support, contract_file, shipment status,
    fees, faults, and ticket status — no document search needed.

    For order-specific policy (cancellation, credits) use get_applicable_rules when you have an order id.
    If an order id is not found, call entity=orders (no filters) to list the customer's orders
    and resolve the closest match before answering.
    """
    user_context = state.get("user_context") or {"role": "customer", "account_id": ""}
    return query_json(entity, filters or {}, user_context)
