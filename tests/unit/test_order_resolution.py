from unittest.mock import patch

from app.services.order_resolution import resolve_order

ACCT_001 = {"role": "customer", "account_id": "ACCT-001"}


def test_resolve_exact_order():
    order = {"order_id": "ORD-1001", "account_id": "ACCT-001", "status": "BOOKED"}

    with patch("app.services.order_resolution.fetch_one", return_value=order):
        result = resolve_order("ORD-1001", ACCT_001)

    assert result["match_type"] == "exact"
    assert result["order"]["order_id"] == "ORD-1001"
    assert result["suggestions"] == []


def test_resolve_ord1001_normalizes_to_ord_1001():
    order = {"order_id": "ORD-1001", "account_id": "ACCT-001", "status": "BOOKED"}

    def fake_fetch_one(sql, params):
        if params == ("ORD-1001",):
            return order
        return None

    with patch("app.services.order_resolution.fetch_one", side_effect=fake_fetch_one):
        result = resolve_order("ord1001", ACCT_001)

    assert result["match_type"] == "exact"
    assert result["resolved_order_id"] == "ORD-1001"


def test_resolve_fuzzy_001_to_ord_1001():
    orders = [
        {"order_id": "ORD-1001", "account_id": "ACCT-001", "status": "BOOKED"},
        {"order_id": "ORD-1002", "account_id": "ACCT-001", "status": "PICKED_UP"},
    ]

    with patch("app.services.order_resolution.fetch_one", return_value=None), patch(
        "app.services.order_resolution.fetch_all", return_value=orders
    ):
        result = resolve_order("001", ACCT_001)

    assert result["match_type"] == "fuzzy"
    assert result["resolved_order_id"] == "ORD-1001"


def test_resolve_ord2001_not_in_account():
    order_2001 = {"order_id": "ORD-2001", "account_id": "ACCT-002", "status": "BOOKED"}

    with patch("app.services.order_resolution.fetch_one", return_value=order_2001):
        result = resolve_order("ORD-2001", ACCT_001)

    assert result["match_type"] == "not_in_account"
    assert result["order"] is None
    assert result["suggestions"] == []


def test_resolve_not_found_no_suggestions():
    orders = [{"order_id": "ORD-1001", "account_id": "ACCT-001", "status": "BOOKED"}]

    with patch("app.services.order_resolution.fetch_one", return_value=None), patch(
        "app.services.order_resolution.fetch_all", return_value=orders
    ):
        result = resolve_order("ORD-9999", ACCT_001)

    assert result["match_type"] == "not_found"
    assert result["order"] is None
    assert result["suggestions"] == []
