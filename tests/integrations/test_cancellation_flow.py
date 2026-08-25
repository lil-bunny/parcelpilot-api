from unittest.mock import patch

import pytest

from app.services.operational_data import UnauthorizedError, query
from app.services.applicable_rules import fetch_applicable_rules
from tests.fixtures.docs import LUMENWORKS, NORTHSTAR, SOP_CURRENT


ACCT_001 = {"role": "customer", "account_id": "ACCT-001"}
ACCT_002 = {"role": "customer", "account_id": "ACCT-002"}


@pytest.fixture
def order_1001():
    return {
        "order_id": "ORD-1001",
        "account_id": "ACCT-001",
        "status": "BOOKED",
        "pickup_actual_at": None,
    }


@pytest.fixture
def order_2001():
    return {
        "order_id": "ORD-2001",
        "account_id": "ACCT-002",
        "status": "BOOKED",
        "pickup_actual_at": None,
    }


@pytest.fixture
def northstar_account():
    return {
        "account_id": "ACCT-001",
        "account_name": "Northstar Logistics",
        "contract_file": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
    }


@pytest.fixture
def lumenworks_account():
    return {
        "account_id": "ACCT-002",
        "account_name": "LumenWorks",
        "contract_file": "06_LumenWorks_Service_Agreement.pdf",
    }


def test_ord_1001_no_lumenworks_agreement(order_1001, northstar_account, monkeypatch):
    def fake_fetch_one(sql, params):
        if params == ("ORD-1001",):
            return order_1001
        if params == ("ACCT-001",):
            return northstar_account
        return None

    def fake_query(entity, filters, user_context):
        if entity == "account":
            return northstar_account
        return None

    def fake_search(query, k=6, filters=None):
        f = filters or {}
        if f.get("document_name"):
            return [NORTHSTAR]
        return [SOP_CURRENT]

    monkeypatch.setattr("app.services.order_resolution.fetch_one", fake_fetch_one)
    monkeypatch.setattr("app.services.applicable_rules.query", fake_query)
    monkeypatch.setattr("app.services.applicable_rules.search", fake_search)

    result = fetch_applicable_rules("ORD-1001", "cancellation", ACCT_001)
    types = {e["document_type"] for e in result["agreement_evidence"]}
    assert result["order_match"]["match_type"] == "exact"
    assert "northstar_agreement" in types or result["agreement_evidence"]
    assert "lumenworks_agreement" not in types


def test_ord_2001_lumenworks_only(order_2001, lumenworks_account, monkeypatch):
    def fake_fetch_one(sql, params):
        if params == ("ORD-2001",):
            return order_2001
        if params == ("ACCT-002",):
            return lumenworks_account
        return None

    def fake_query(entity, filters, user_context):
        if entity == "account":
            return lumenworks_account
        return None

    def fake_search(query, k=6, filters=None):
        f = filters or {}
        if f.get("document_name"):
            return [LUMENWORKS]
        return [SOP_CURRENT]

    monkeypatch.setattr("app.services.order_resolution.fetch_one", fake_fetch_one)
    monkeypatch.setattr("app.services.applicable_rules.query", fake_query)
    monkeypatch.setattr("app.services.applicable_rules.search", fake_search)

    result = fetch_applicable_rules("ORD-2001", "cancellation", ACCT_002)
    types = {e["document_type"] for e in result["agreement_evidence"]}
    assert "lumenworks_agreement" in types
    assert "northstar_agreement" not in types


def test_ord_1001_fuzzy_from_partial_id(order_1001, northstar_account, monkeypatch):
    def fake_fetch_one(sql, params):
        if params == ("ACCT-001",):
            return northstar_account
        return None

    def fake_fetch_all(sql, params):
        return [order_1001]

    def fake_query(entity, filters, user_context):
        if entity == "account":
            return northstar_account
        return None

    def fake_search(query, k=6, filters=None):
        f = filters or {}
        if f.get("document_name"):
            return [NORTHSTAR]
        return [SOP_CURRENT]

    monkeypatch.setattr("app.services.order_resolution.fetch_one", fake_fetch_one)
    monkeypatch.setattr("app.services.order_resolution.fetch_all", fake_fetch_all)
    monkeypatch.setattr("app.services.applicable_rules.query", fake_query)
    monkeypatch.setattr("app.services.applicable_rules.search", fake_search)

    result = fetch_applicable_rules("001", "cancellation", ACCT_001)
    assert result["order_match"]["match_type"] == "fuzzy"
    assert result["order"]["order_id"] == "ORD-1001"


def test_northstar_user_cannot_access_ord_2001(order_2001):
    with patch("app.services.order_resolution.fetch_one", return_value=order_2001):
        row = query("order", {"order_id": "ORD-2001"}, ACCT_001)
    assert row is None


def test_status_only_postgres(order_1001):
    with patch("app.services.order_resolution.fetch_one", return_value=order_1001):
        row = query("order", {"order_id": "ORD-1001"}, ACCT_001)
    assert row["status"] == "BOOKED"
