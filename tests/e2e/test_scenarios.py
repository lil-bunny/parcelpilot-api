import json
from unittest.mock import patch

from app.services.operational_data import query_json
from app.tools.definitions.calculate_service_credit import compute_credit
from app.tools.definitions.search_documents import search_documents


def test_multi_step_order_then_policy_mocked():
    order = {
        "order_id": "ORD-1001",
        "account_id": "ACCT-001",
        "status": "booked",
        "pickup_window_start": "2026-01-01T10:00:00",
    }
    account = {
        "account_id": "ACCT-001",
        "account_name": "Northstar Logistics",
        "contract_file": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
    }
    ctx = {"role": "customer", "account_id": "ACCT-001"}

    with patch("app.services.order_resolution.fetch_one", return_value=order), patch(
        "app.services.operational_data.fetch_one", return_value=account
    ):
        order_raw = query_json("order", {"order_id": "ORD-1001"}, ctx)
        acct_raw = query_json("account", {"account_id": "ACCT-001"}, ctx)

    order_data = json.loads(order_raw)["data"]
    account_data = json.loads(acct_raw)["data"]
    assert order_data["order_id"] == "ORD-1001"
    assert "Northstar" in account_data["account_name"]
    assert account_data["contract_file"]


def test_service_credit_scenario():
    facts = {
        "delay_hours": 3,
        "carrier_fault": True,
        "customer_fault": False,
        "shipment_fee_inr": 800,
    }
    evidence = [
        "Service credits apply when carrier fault causes delay of at least 2 hours.",
        "Eligible credits are 15% of the shipment fee.",
    ]
    result = compute_credit(facts, evidence)
    assert result["eligible"] is True
    assert result["credit_amount"] == 120.0


def test_search_documents_returns_json():
    with patch("app.tools.definitions.search_documents.search", return_value=[]):
        raw = search_documents.invoke(
            {
                "query": "cancellation policy",
                "filters": None,
                "state": {"user_context": {"role": "internal"}},
            }
        )
    payload = json.loads(raw)
    assert "evidence" in payload
    assert "summary" in payload
