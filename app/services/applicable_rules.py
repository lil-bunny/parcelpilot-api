from __future__ import annotations

import json

from app.services.hybrid_retriever import format_hits, search, to_evidence
from app.services.operational_data import OperationalError, UnauthorizedError, query
from app.services.order_resolution import resolve_order

_TOPIC_SOP = frozenset({"cancellation", "cancel", "service_credit", "credit", "fee"})
_TOPIC_POLICY = frozenset({"sla", "support", "policy", "p2", "response"})
_TOPIC_OPS = frozenset({"swiftship", "webhook", "product", "booked", "status"})


def _sop_filters(topic: str) -> dict:
    t = topic.lower()
    if any(w in t for w in _TOPIC_OPS):
        return {"document_type": "product_ops", "status": "current"}
    if any(w in t for w in _TOPIC_POLICY):
        return {"document_type": "support_policy", "status": "current"}
    return {"document_type": "cancellation_sop", "status": "current"}


def _account_payload(account: dict) -> dict:
    return {
        "account_id": account.get("account_id"),
        "account_name": account.get("account_name"),
        "contract_file": account.get("contract_file"),
        "plan": account.get("plan"),
    }


def _fetch_agreement_and_policy(account: dict, topic: str) -> tuple[list, list]:
    contract_file = account.get("contract_file")
    agreement_docs = []
    if contract_file:
        agreement_docs = search(topic, k=4, filters={"document_name": contract_file})
    policy_docs = search(topic, k=4, filters=_sop_filters(topic))
    return agreement_docs, policy_docs


def _policy_result(account: dict, agreement_docs: list, policy_docs: list) -> dict:
    acct = _account_payload(account)
    return {
        "account": acct,
        "agreement_evidence": to_evidence(agreement_docs),
        "policy_evidence": to_evidence(policy_docs),
        "agreement_summary": format_hits(agreement_docs),
        "policy_summary": format_hits(policy_docs),
    }


def fetch_account_policy(topic: str, user_context: dict) -> dict:
    """Auth account → customer agreement + topic-appropriate global policy only."""
    account = query("account", {}, user_context)
    if not account:
        return {"error": "not_found", "message": "Account not found."}
    agreement_docs, policy_docs = _fetch_agreement_and_policy(account, topic)
    return _policy_result(account, agreement_docs, policy_docs)


def fetch_applicable_rules(order_id: str, topic: str, user_context: dict) -> dict:
    """Order → account → contract_file → filtered agreement + SOP."""
    resolution = resolve_order(order_id, user_context)
    if resolution["order"] is None:
        display_id = resolution.get("display_order_id") or resolution["requested_order_id"]
        return {
            "error": "not_found",
            "message": f"I couldn't find {display_id} in your account.",
            "requested_order_id": resolution["requested_order_id"],
        }

    order = resolution["order"]
    account = query("account", {"account_id": order["account_id"]}, user_context)
    if not account:
        return {"error": "not_found", "message": f"Account {order['account_id']} not found."}

    agreement_docs, policy_docs = _fetch_agreement_and_policy(account, topic)
    result = _policy_result(account, agreement_docs, policy_docs)
    result["order_match"] = {
        "requested": resolution["requested_order_id"],
        "resolved": resolution["resolved_order_id"],
        "match_type": resolution["match_type"],
    }
    result["order"] = order
    return result


def fetch_account_policy_json(topic: str, user_context: dict) -> str:
    try:
        result = fetch_account_policy(topic, user_context)
    except UnauthorizedError as exc:
        return json.dumps({"error": "unauthorized", "message": str(exc)})
    except OperationalError as exc:
        return json.dumps({"error": "invalid_request", "message": str(exc)})
    except Exception as exc:
        return json.dumps({"error": "database_unavailable", "message": str(exc)})
    return json.dumps(result, default=str)


def fetch_applicable_rules_json(order_id: str, topic: str, user_context: dict) -> str:
    try:
        result = fetch_applicable_rules(order_id, topic, user_context)
    except UnauthorizedError as exc:
        return json.dumps({"error": "unauthorized", "message": str(exc)})
    except OperationalError as exc:
        return json.dumps({"error": "invalid_request", "message": str(exc)})
    except Exception as exc:
        return json.dumps({"error": "database_unavailable", "message": str(exc)})
    return json.dumps(result, default=str)
