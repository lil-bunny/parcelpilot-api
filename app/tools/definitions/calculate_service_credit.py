from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.tools import tool


def _parse_hours(text: str) -> list[float]:
    return [float(m.group(1)) for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b", text, re.I)]


def _parse_percent_credit(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:of\s+(?:the\s+)?)?(?:shipment\s+)?fee", text, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*%.{0,30}fee", text, re.I)
    return float(m.group(1)) if m else None


def _parse_flat_credit(text: str) -> float | None:
    m = re.search(r"(?:credit|refund)\s*(?:of\s*)?(?:INR|Rs\.?|₹)?\s*(\d+(?:\.\d+)?)", text, re.I)
    return float(m.group(1)) if m else None


def compute_credit(facts: dict[str, Any], evidence: list[str]) -> dict[str, Any]:
    """Deterministic eligibility from facts + evidence text. No hardcoded customer outcomes."""
    delay_hours = facts.get("delay_hours")
    if delay_hours is None:
        delay_hours = facts.get("delay_hours_actual")
    carrier_fault = facts.get("carrier_fault")
    customer_fault = facts.get("customer_fault")
    fee = facts.get("shipment_fee_inr") or facts.get("fee") or 0
    try:
        fee = float(fee)
    except (TypeError, ValueError):
        fee = 0.0

    combined = "\n".join(evidence)
    thresholds = _parse_hours(combined)
    min_delay = min(thresholds) if thresholds else None

    reasons = []
    if customer_fault is True:
        return {
            "eligible": False,
            "credit_amount": 0.0,
            "reasoning_summary": "Customer fault recorded on the order; service credit not applicable.",
            "evidence_used": evidence[:3],
        }
    if carrier_fault is not True:
        reasons.append("carrier_fault is not true on the order facts")
    if delay_hours is None:
        reasons.append("delay_hours not provided in facts")
    elif min_delay is not None and float(delay_hours) < min_delay:
        return {
            "eligible": False,
            "credit_amount": 0.0,
            "reasoning_summary": f"Delay {delay_hours}h is below the {min_delay}h threshold in evidence.",
            "evidence_used": evidence[:3],
        }

    if carrier_fault is True and delay_hours is not None and (min_delay is None or float(delay_hours) >= min_delay):
        pct = _parse_percent_credit(combined)
        flat = _parse_flat_credit(combined)
        if pct is not None:
            amount = round(fee * pct / 100, 2)
            return {
                "eligible": True,
                "credit_amount": amount,
                "reasoning_summary": f"Delay {delay_hours}h with carrier fault meets threshold; {pct}% of fee.",
                "evidence_used": evidence[:3],
            }
        if flat is not None:
            return {
                "eligible": True,
                "credit_amount": flat,
                "reasoning_summary": f"Delay {delay_hours}h with carrier fault meets threshold; flat credit.",
                "evidence_used": evidence[:3],
            }
        return {
            "eligible": True,
            "credit_amount": None,
            "reasoning_summary": "Delay and carrier fault meet threshold but credit amount is not numeric in evidence.",
            "evidence_used": evidence[:3],
        }

    return {
        "eligible": False,
        "credit_amount": 0.0,
        "reasoning_summary": "; ".join(reasons) or "Insufficient facts or evidence to determine eligibility.",
        "evidence_used": evidence[:3],
    }


@tool
def calculate_service_credit(facts: dict, evidence: list[str]) -> str:
    """Calculate service-credit eligibility from operational facts and policy evidence snippets.

    Call after query_operational_data and search_documents. Pass delay_hours, carrier_fault,
    customer_fault, shipment_fee_inr in facts. Pass relevant text snippets in evidence.
    """
    result = compute_credit(facts or {}, evidence or [])
    return json.dumps(result)
