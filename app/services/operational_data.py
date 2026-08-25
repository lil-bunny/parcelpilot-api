from __future__ import annotations

import json
from typing import Any

from app.integrations.db.postgres import fetch_all, fetch_one
from app.services.order_resolution import resolve_order

ENTITIES = frozenset({"account", "order", "ticket", "orders", "tickets"})


class OperationalError(Exception):
    pass


class UnauthorizedError(OperationalError):
    pass


def _require_customer_account(user_context: dict[str, Any]) -> str:
    role = user_context.get("role", "customer")
    account_id = (user_context.get("account_id") or "").strip()
    if role == "customer" and not account_id:
        raise OperationalError("Missing account_id in user_context")
    return account_id


def query(entity: str, filters: dict[str, Any], user_context: dict[str, Any]) -> Any:
    entity = entity.strip().lower()
    if entity not in ENTITIES:
        raise OperationalError(f"Unknown entity: {entity}. Use account, order, ticket, orders, or tickets.")

    filters = {k: v for k, v in (filters or {}).items() if v is not None and str(v).strip() != ""}
    role = user_context.get("role", "customer")
    auth_account = _require_customer_account(user_context) if role == "customer" else None

    if entity == "account":
        account_id = filters.get("account_id") or auth_account
        if not account_id:
            raise OperationalError("account_id filter required")
        if role == "customer" and account_id != auth_account:
            raise UnauthorizedError("Not authorized for this account")
        row = fetch_one("SELECT * FROM accounts WHERE account_id = %s", (account_id,))
        return row

    if entity == "order":
        order_id = filters.get("order_id")
        if not order_id:
            raise OperationalError("order_id filter required")
        resolution = resolve_order(str(order_id), user_context)
        return resolution.get("order")

    if entity == "ticket":
        ticket_id = filters.get("ticket_id")
        if not ticket_id:
            raise OperationalError("ticket_id filter required")
        row = fetch_one("SELECT * FROM tickets WHERE ticket_id = %s", (ticket_id,))
        if row is None:
            return None
        if role == "customer" and row["account_id"] != auth_account:
            raise UnauthorizedError("Not authorized for this ticket")
        return row

    if entity == "orders":
        account_id = filters.get("account_id") or auth_account
        if role == "customer" and account_id != auth_account:
            raise UnauthorizedError("Not authorized for these orders")
        return fetch_all("SELECT * FROM orders WHERE account_id = %s ORDER BY order_id", (account_id,))

    if entity == "tickets":
        account_id = filters.get("account_id") or auth_account
        if role == "customer" and account_id != auth_account:
            raise UnauthorizedError("Not authorized for these tickets")
        return fetch_all("SELECT * FROM tickets WHERE account_id = %s ORDER BY ticket_id", (account_id,))

    raise OperationalError(f"Unknown entity: {entity}")


def query_json(entity: str, filters: dict[str, Any], user_context: dict[str, Any]) -> str:
    entity_key = entity.strip().lower()
    filters = {k: v for k, v in (filters or {}).items() if v is not None and str(v).strip() != ""}

    if entity_key == "order" and filters.get("order_id"):
        try:
            resolution = resolve_order(str(filters["order_id"]), user_context)
        except OperationalError as exc:
            return json.dumps({"error": "invalid_request", "message": str(exc)})
        except Exception as exc:
            return json.dumps({"error": "database_unavailable", "message": str(exc)})
        if resolution.get("order"):
            return json.dumps({"found": True, "data": resolution["order"]}, default=str)
        display_id = resolution.get("display_order_id") or resolution.get("requested_order_id")
        return json.dumps(
            {
                "found": False,
                "requested_order_id": display_id,
                "message": f"I couldn't find {display_id} in your account.",
            }
        )

    try:
        result = query(entity, filters, user_context)
    except UnauthorizedError as exc:
        return json.dumps({"error": "unauthorized", "message": str(exc)})
    except OperationalError as exc:
        return json.dumps({"error": "invalid_request", "message": str(exc)})
    except Exception as exc:
        return json.dumps({"error": "database_unavailable", "message": str(exc)})
    if result is None:
        return json.dumps({"found": False})
    return json.dumps({"found": True, "data": result}, default=str)
