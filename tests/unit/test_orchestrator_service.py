import json

from app.services.orchestrator_service import _collect_evidence


def test_collect_evidence_empty_sources_for_postgres_only_turn():
    trace = [
        {
            "ok": True,
            "name": "query_operational_data",
            "result": json.dumps(
                {
                    "found": True,
                    "data": {
                        "account_id": "ACCT-001",
                        "plan": "Enterprise",
                        "csm": "Priya Mehta",
                    },
                }
            ),
        }
    ]
    evidence, sources, conflicts, _confidence = _collect_evidence(trace)
    assert sources == []
    assert evidence == []


def test_collect_evidence_ignores_postgres_only_search_error():
    trace = [
        {
            "ok": True,
            "name": "search_documents",
            "result": json.dumps(
                {"error": "postgres_only", "message": "Use query_operational_data(entity=account)."}
            ),
        },
        {
            "ok": True,
            "name": "query_operational_data",
            "result": json.dumps({"found": True, "data": {"plan": "Enterprise", "csm": "Priya Mehta"}}),
        },
    ]
    _, sources, _, _ = _collect_evidence(trace)
    assert sources == []


def test_system_prompt_routes_account_facts_to_postgres():
    from app.workflows.graph.orchestrator import _SYSTEM

    assert "Postgres ONLY" in _SYSTEM
    assert "plan, CSM" in _SYSTEM
    assert "get_account_policy" in _SYSTEM


def test_collect_evidence_includes_get_account_policy():
    trace = [
        {
            "ok": True,
            "name": "get_account_policy",
            "result": json.dumps(
                {
                    "account": {
                        "account_id": "ACCT-001",
                        "contract_file": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
                    },
                    "agreement_evidence": [
                        {
                            "document_type": "northstar_agreement",
                            "document_name": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
                            "postgres_account_id": "ACCT-001",
                            "authority": 4,
                            "status": "current",
                        }
                    ],
                    "policy_evidence": [
                        {
                            "document_type": "support_policy",
                            "document_name": "01_Support_Policy_v3_CURRENT.pdf",
                            "authority": 2,
                            "status": "current",
                        }
                    ],
                }
            ),
        }
    ]
    evidence, sources, _, _ = _collect_evidence(trace, auth_account_id="ACCT-001")
    assert len(sources) == 2
    doc_types = {e.get("document_type") for e in evidence}
    assert "northstar_agreement" in doc_types
    assert "support_policy" in doc_types
    assert "lumenworks_agreement" not in doc_types
