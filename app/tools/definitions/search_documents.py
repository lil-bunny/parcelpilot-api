import json

from langchain_core.tools import tool
from typing_extensions import Annotated

from app.domain.postgres_only import POSTGRES_ONLY_TOOL_HINT, is_postgres_only_question
from app.services.hybrid_retriever import AGREEMENT_DOC_IDS, format_hits, search, to_evidence
from langgraph.prebuilt import InjectedState

_ACCOUNT_SCOPED_HINT = "Use get_account_policy(topic) for customer SLA/support policy questions."

# Narrow doc_type filters are allowed; bare semantic search is not.
_SCOPED_DOC_TYPES = frozenset({"support_policy", "cancellation_sop", "product_ops"})


def is_agreement_search(filters: dict | None) -> bool:
    if not filters:
        return False
    return filters.get("document_type") in AGREEMENT_DOC_IDS


def _has_account_scope(filters: dict) -> bool:
    if filters.get("customer_account_id") or filters.get("document_name"):
        return True
    doc_type = filters.get("document_type")
    return doc_type in _SCOPED_DOC_TYPES or doc_type in AGREEMENT_DOC_IDS


@tool
def search_documents(
    query: str,
    filters: dict | None,
    state: Annotated[dict, InjectedState],
) -> str:
    """Search policies, SOPs, product docs, and customer agreements (hybrid vector + keyword).

    Prefer get_account_policy(topic) for customer SLA/support without an order id.
    Prefer get_applicable_rules for order-specific cancellation/credit questions.
    NOT for plan, CSM, or account_name — use query_operational_data(entity=account).

    filters: status (current|deprecated), document_type, document_name, customer_account_id.
    Customer agreement searches require document_name or customer_account_id.
    """
    if is_postgres_only_question(query):
        return json.dumps({"error": "postgres_only", "message": POSTGRES_ONLY_TOOL_HINT})

    f = filters or {}
    ctx = (state or {}).get("user_context") or {}
    if ctx.get("role") == "customer" and ctx.get("account_id") and not _has_account_scope(f):
        return json.dumps({"error": "account_scoped_required", "message": _ACCOUNT_SCOPED_HINT})

    if is_agreement_search(f):
        if not f.get("document_name") and not f.get("customer_account_id"):
            return json.dumps(
                {
                    "error": "filter_required",
                    "message": (
                        "Customer agreement searches require document_name (from contract_file) "
                        "or customer_account_id. Use get_applicable_rules for order-specific questions."
                    ),
                }
            )
    if f.get("document_type") in AGREEMENT_DOC_IDS and not f.get("document_name") and not f.get(
        "customer_account_id"
    ):
        return json.dumps(
            {
                "error": "filter_required",
                "message": "Pass document_name or customer_account_id to retrieve a customer agreement.",
            }
        )

    docs = search(query, filters=f or None)
    payload = {"evidence": to_evidence(docs), "summary": format_hits(docs)}
    return json.dumps(payload, default=str)
