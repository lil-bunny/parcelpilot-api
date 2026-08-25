from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from app.integrations.db.postgres import fetch_all, fetch_one

_MIN_SCORE = 72.0
_ORDER_RE = re.compile(r"ORD-?\d+", re.I)


def _digits(order_id: str) -> str:
    return re.sub(r"\D", "", order_id or "")


def normalize_order_id(raw: str) -> str | None:
    match = _ORDER_RE.search(raw or "")
    if not match:
        return None
    digits = _digits(match.group(0))
    return f"ORD-{digits}" if digits else match.group(0).upper()


def _score_match(requested: str, candidate_id: str) -> float:
    rq = (requested or "").strip()
    cd = (candidate_id or "").strip()
    if rq.upper() == cd.upper():
        return 100.0
    rq_d, cd_d = _digits(rq), _digits(cd)
    if rq_d == cd_d:
        return 95.0
    if cd_d.endswith(rq_d) or rq_d.endswith(cd_d):
        return 85.0
    return SequenceMatcher(None, rq.upper(), cd.upper()).ratio() * 100


def _auth_account(user_context: dict[str, Any]) -> str | None:
    if user_context.get("role", "customer") != "customer":
        return None
    return (user_context.get("account_id") or "").strip() or None


def _fetch_order_row(order_id: str) -> dict | None:
    return fetch_one("SELECT * FROM orders WHERE order_id = %s", (order_id,))


def _try_exact(requested: str, auth_account: str | None) -> dict[str, Any] | None:
    candidates = [requested]
    normalized = normalize_order_id(requested)
    if normalized and normalized not in candidates:
        candidates.append(normalized)

    seen_other_tenant = False
    for oid in candidates:
        row = _fetch_order_row(oid)
        if row is None:
            continue
        if auth_account and row["account_id"] != auth_account:
            seen_other_tenant = True
            continue
        return {
            "requested_order_id": requested,
            "resolved_order_id": row["order_id"],
            "order": row,
            "match_type": "exact",
            "suggestions": [],
        }

    if seen_other_tenant:
        display_id = normalized or requested
        return {
            "requested_order_id": requested,
            "resolved_order_id": None,
            "order": None,
            "match_type": "not_in_account",
            "display_order_id": display_id,
            "suggestions": [],
        }
    return None


def resolve_order(requested_id: str, user_context: dict[str, Any]) -> dict[str, Any]:
    requested = (requested_id or "").strip()
    auth_account = _auth_account(user_context)

    exact = _try_exact(requested, auth_account)
    if exact is not None:
        return exact

    account_id = auth_account or user_context.get("account_id")
    candidates = (
        fetch_all("SELECT * FROM orders WHERE account_id = %s ORDER BY order_id", (account_id,))
        if account_id
        else []
    )
    candidates = candidates or []

    scored = sorted(
        ((o, _score_match(requested, o["order_id"])) for o in candidates),
        key=lambda x: -x[1],
    )
    suggestions = [
        {"order_id": o["order_id"], "status": o.get("status"), "score": round(score, 2)}
        for o, score in scored[:3]
        if score >= _MIN_SCORE
    ]

    if scored and scored[0][1] >= _MIN_SCORE:
        best = scored[0][0]
        return {
            "requested_order_id": requested,
            "resolved_order_id": best["order_id"],
            "order": best,
            "match_type": "fuzzy",
            "match_score": round(scored[0][1], 2),
            "suggestions": suggestions,
        }

    display_id = normalize_order_id(requested) or requested
    return {
        "requested_order_id": requested,
        "resolved_order_id": None,
        "order": None,
        "match_type": "not_found",
        "display_order_id": display_id,
        "suggestions": [],
    }
