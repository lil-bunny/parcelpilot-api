from app.domain.evidence import resolve_evidence
from app.services.hybrid_retriever import doc_matches_filters, merge_and_rank, to_evidence
from app.services.applicable_rules import fetch_applicable_rules, fetch_account_policy
from app.tools.definitions.search_documents import search_documents
from app.tools.registry import all_tools
from tests.fixtures.docs import KEYWORD_ONLY, LUMENWORKS, NORTHSTAR, POLICY_DEPRECATED, SOP_CURRENT, SUPPORT_POLICY


def test_merge_keeps_keyword_only_hit():
    merged = merge_and_rank([SOP_CURRENT], [KEYWORD_ONLY], k=6)
    ids = {d.metadata["chunk_id"] for d in merged}
    assert ids == {"sop", "keyword"}


def test_merge_two_sources_dedupes():
    merged = merge_and_rank([SOP_CURRENT, NORTHSTAR], [NORTHSTAR, KEYWORD_ONLY], k=6)
    ids = [d.metadata["chunk_id"] for d in merged]
    assert ids == ["northstar", "sop", "keyword"]


def test_deprecated_never_above_current_higher_authority():
    merged = merge_and_rank([POLICY_DEPRECATED], [SOP_CURRENT], k=2)
    assert merged[0].metadata["chunk_id"] == "sop"
    assert merged[0].metadata["status"] == "current"
    assert merged[-1].metadata["status"] == "deprecated"


def test_doc_matches_document_name():
    assert doc_matches_filters(
        NORTHSTAR.metadata,
        {"document_name": "05_Northstar_Logistics_Enterprise_Agreement.pdf"},
    )
    assert not doc_matches_filters(
        LUMENWORKS.metadata,
        {"document_name": "05_Northstar_Logistics_Enterprise_Agreement.pdf"},
    )


def test_doc_matches_customer_account_id():
    assert doc_matches_filters(NORTHSTAR.metadata, {"customer_account_id": "ACCT-001"})
    assert not doc_matches_filters(LUMENWORKS.metadata, {"customer_account_id": "ACCT-001"})


def test_strict_filter_empty_not_fallback():
    merged = merge_and_rank([NORTHSTAR, LUMENWORKS, SOP_CURRENT], [], k=6)
    filtered = [d for d in merged if doc_matches_filters(d.metadata, {"customer_account_id": "ACCT-001"})]
    assert len(filtered) == 1
    assert filtered[0].metadata["chunk_id"] == "northstar"


def test_to_evidence_postgres_account_id():
    ev = to_evidence([NORTHSTAR])[0]
    assert ev["postgres_account_id"] == "ACCT-001"


def test_registry_has_get_applicable_rules():
    names = {t.name for t in all_tools()}
    assert "get_applicable_rules" in names
    assert "get_account_policy" in names
    assert "search_documents" in names


def test_search_documents_blocks_customer_unscoped_search():
    raw = search_documents.invoke(
        {
            "query": "P2 SLA Enterprise",
            "filters": None,
            "state": {"user_context": {"role": "customer", "account_id": "ACCT-001"}},
        }
    )
    assert "account_scoped_required" in raw


def test_search_documents_blocks_unfiltered_agreement():
    raw = search_documents.invoke(
        {
            "query": "cancellation agreement",
            "filters": {"document_type": "northstar_agreement"},
            "state": {"user_context": {"role": "internal"}},
        }
    )
    assert "filter_required" in raw


def test_search_documents_blocks_postgres_only_account_questions():
    raw = search_documents.invoke(
        {
            "query": "What plan am I on and who is my CSM?",
            "filters": None,
            "state": {"user_context": {"role": "customer", "account_id": "ACCT-001"}},
        }
    )
    assert "postgres_only" in raw


def test_evidence_skips_non_dict_structured_rows():
    structured = [
        {"order_id": "ORD-1001", "account_id": "ACCT-001"},
        [{"order_id": "ORD-1002", "account_id": "ACCT-002"}],
    ]
    resolved = resolve_evidence(structured, [])
    assert resolved["confidence"] == 0.2


def test_evidence_drops_wrong_agreement():
    structured = [{"account_id": "ACCT-001", "contract_file": "05_Northstar_Logistics_Enterprise_Agreement.pdf"}]
    docs = [
        {"document_type": "northstar_agreement", "postgres_account_id": "ACCT-001", "document_name": "05_Northstar.pdf", "authority": 4, "status": "current"},
        {"document_type": "lumenworks_agreement", "postgres_account_id": "ACCT-002", "document_name": "06_LumenWorks.pdf", "authority": 4, "status": "current"},
        {"document_type": "cancellation_sop", "document_name": "03_SOP.pdf", "authority": 3, "status": "current"},
    ]
    resolved = resolve_evidence(structured, docs)
    names = {d.get("document_type") for d in resolved["evidence"]}
    assert "lumenworks_agreement" not in names
    assert "northstar_agreement" in names


def test_evidence_auth_account_id_drops_wrong_agreement():
    docs = [
        {"document_type": "northstar_agreement", "postgres_account_id": "ACCT-001", "document_name": "05_Northstar.pdf", "authority": 4, "status": "current"},
        {"document_type": "lumenworks_agreement", "postgres_account_id": "ACCT-002", "document_name": "06_LumenWorks.pdf", "authority": 4, "status": "current"},
    ]
    resolved = resolve_evidence([], docs, auth_account_id="ACCT-001")
    names = {d.get("document_type") for d in resolved["evidence"]}
    assert "lumenworks_agreement" not in names
    assert "northstar_agreement" in names


def test_fetch_account_policy_mocked(monkeypatch):
    account = {
        "account_id": "ACCT-001",
        "account_name": "Northstar Logistics",
        "contract_file": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
    }
    ctx = {"role": "customer", "account_id": "ACCT-001"}

    def fake_query(entity, filters, user_context):
        return account

    def fake_search(query, k=6, filters=None):
        if filters and filters.get("document_name"):
            return [NORTHSTAR]
        if filters and filters.get("document_type") == "support_policy":
            return [SUPPORT_POLICY]
        return [LUMENWORKS, SOP_CURRENT]

    monkeypatch.setattr("app.services.applicable_rules.query", fake_query)
    monkeypatch.setattr("app.services.applicable_rules.search", fake_search)

    result = fetch_account_policy("sla P2", ctx)
    agreement_types = {e["document_type"] for e in result["agreement_evidence"]}
    policy_types = {e["document_type"] for e in result["policy_evidence"]}
    assert agreement_types == {"northstar_agreement"}
    assert policy_types == {"support_policy"}
    assert "lumenworks_agreement" not in agreement_types


def test_fetch_applicable_rules_mocked(monkeypatch):
    order = {"order_id": "ORD-1001", "account_id": "ACCT-001", "status": "BOOKED"}
    account = {
        "account_id": "ACCT-001",
        "account_name": "Northstar Logistics",
        "contract_file": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
    }
    ctx = {"role": "customer", "account_id": "ACCT-001"}

    def fake_fetch_one(sql, params):
        if params == ("ORD-1001",):
            return order
        return None

    def fake_query(entity, filters, user_context):
        if entity == "account":
            return account
        return None

    def fake_search(query, k=6, filters=None):
        if filters and filters.get("document_name"):
            return [NORTHSTAR]
        if filters and filters.get("document_type") == "cancellation_sop":
            return [SOP_CURRENT]
        return [NORTHSTAR, LUMENWORKS]

    monkeypatch.setattr("app.services.order_resolution.fetch_one", fake_fetch_one)
    monkeypatch.setattr("app.services.applicable_rules.query", fake_query)
    monkeypatch.setattr("app.services.applicable_rules.search", fake_search)

    result = fetch_applicable_rules("ORD-1001", "cancellation", ctx)
    agreement_types = {e["document_type"] for e in result["agreement_evidence"]}
    assert "lumenworks_agreement" not in agreement_types
    assert result["order"]["order_id"] == "ORD-1001"
