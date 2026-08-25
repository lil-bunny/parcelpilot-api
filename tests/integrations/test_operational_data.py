from unittest.mock import patch

import pytest

from app.services.operational_data import UnauthorizedError, query, query_json


ACCT_001 = {"role": "customer", "account_id": "ACCT-001"}
ACCT_002 = {"role": "customer", "account_id": "ACCT-002"}


@pytest.fixture
def order_row():
    return {
        "order_id": "ORD-1001",
        "account_id": "ACCT-001",
        "status": "booked",
        "carrier_fault": False,
        "customer_fault": False,
        "shipment_fee_inr": 500,
    }


@pytest.fixture
def account_row():
    return {
        "account_id": "ACCT-001",
        "account_name": "Northstar Logistics",
        "plan": "enterprise",
        "status": "active",
        "contract_file": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
    }


@pytest.fixture
def ticket_row():
    return {
        "ticket_id": "T-1001",
        "account_id": "ACCT-001",
        "status": "open",
        "subject": "Late shipment",
    }


def test_get_order_by_id(order_row):
    with patch("app.services.order_resolution.fetch_one", return_value=order_row):
        row = query("order", {"order_id": "ORD-1001"}, ACCT_001)
    assert row["order_id"] == "ORD-1001"


def test_get_account_by_id(account_row):
    with patch("app.services.operational_data.fetch_one", return_value=account_row):
        row = query("account", {"account_id": "ACCT-001"}, ACCT_001)
    assert row["account_name"] == "Northstar Logistics"


def test_get_ticket_by_id(ticket_row):
    with patch("app.services.operational_data.fetch_one", return_value=ticket_row):
        row = query("ticket", {"ticket_id": "T-1001"}, ACCT_001)
    assert row["ticket_id"] == "T-1001"


def test_customer_can_access_own_order(order_row):
    with patch("app.services.order_resolution.fetch_one", return_value=order_row):
        row = query("order", {"order_id": "ORD-1001"}, ACCT_001)
    assert row is not None


def test_unauthorized_order_access(order_row):
    with patch("app.services.order_resolution.fetch_one", return_value=order_row):
        row = query("order", {"order_id": "ORD-1001"}, ACCT_002)
    assert row is None


def test_unauthorized_ticket_access(ticket_row):
    with patch("app.services.operational_data.fetch_one", return_value=ticket_row):
        with pytest.raises(UnauthorizedError):
            query("ticket", {"ticket_id": "T-1001"}, ACCT_002)


def test_query_json_order_not_in_account(order_row):
    with patch("app.services.order_resolution.fetch_one", return_value=order_row):
        raw = query_json("order", {"order_id": "ORD-1001"}, ACCT_002)
    assert "unauthorized" not in raw
    assert "not found" in raw.lower() or "in your account" in raw.lower()


def test_query_json_ord2001_safe_not_found():
    order_2001 = {
        "order_id": "ORD-2001",
        "account_id": "ACCT-002",
        "status": "BOOKED",
    }
    with patch("app.services.order_resolution.fetch_one", return_value=order_2001):
        raw = query_json("order", {"order_id": "ORD-2001"}, ACCT_001)
    assert "ORD-2001" in raw
    assert "in your account" in raw
    assert "unauthorized" not in raw


def test_list_orders_for_account(order_row):
    with patch("app.services.operational_data.fetch_all", return_value=[order_row]):
        rows = query("orders", {}, ACCT_001)
    assert len(rows) == 1
