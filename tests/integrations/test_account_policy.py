from app.services.applicable_rules import fetch_account_policy
from tests.fixtures.docs import LUMENWORKS, NORTHSTAR, SOP_CURRENT, SUPPORT_POLICY


def test_fetch_account_policy_sla_scoped_to_account_and_support_policy(monkeypatch):
    account = {
        "account_id": "ACCT-001",
        "account_name": "Northstar Logistics",
        "contract_file": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
        "plan": "Enterprise",
    }
    ctx = {"role": "customer", "account_id": "ACCT-001"}

    def fake_query(entity, filters, user_context):
        assert entity == "account"
        return account

    def fake_search(query, k=6, filters=None):
        if filters and filters.get("document_name"):
            return [NORTHSTAR]
        if filters and filters.get("document_type") == "support_policy":
            return [SUPPORT_POLICY]
        if filters and filters.get("document_type") == "cancellation_sop":
            return [SOP_CURRENT]
        return [NORTHSTAR, LUMENWORKS, SOP_CURRENT]

    monkeypatch.setattr("app.services.applicable_rules.query", fake_query)
    monkeypatch.setattr("app.services.applicable_rules.search", fake_search)

    result = fetch_account_policy("P2 SLA Enterprise", ctx)

    agreement_types = {e["document_type"] for e in result["agreement_evidence"]}
    policy_types = {e["document_type"] for e in result["policy_evidence"]}
    policy_names = {e["document_name"] for e in result["policy_evidence"]}

    assert "lumenworks_agreement" not in agreement_types
    assert "northstar_agreement" in agreement_types
    assert policy_types == {"support_policy"}
    assert "01_Support_Policy_v3_CURRENT.pdf" in policy_names
    assert "03_Cancellation_and_Service_Credit_SOP" not in " ".join(policy_names)
    assert result["account"]["account_id"] == "ACCT-001"
