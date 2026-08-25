from __future__ import annotations

from typing import Any


def _account_context(structured: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    account_id = None
    contract_file = None
    for row in structured:
        if not isinstance(row, dict):
            continue
        if row.get("order_id"):
            account_id = row.get("account_id") or account_id
        if row.get("account_name") or row.get("contract_file"):
            account_id = row.get("account_id") or account_id
            contract_file = row.get("contract_file") or contract_file
        if row.get("account") and isinstance(row["account"], dict):
            account_id = row["account"].get("account_id") or account_id
            contract_file = row["account"].get("contract_file") or contract_file
    return account_id, contract_file


def _drop_wrong_agreements(
    docs: list[dict[str, Any]],
    account_id: str | None,
    contract_file: str | None,
) -> list[dict]:
    if not account_id and not contract_file:
        return docs
    out = []
    for d in docs:
        pg = d.get("postgres_account_id")
        slug = d.get("customer_id")
        dtype = str(d.get("document_type") or "")
        is_agreement = dtype.endswith("_agreement") or slug
        if not is_agreement:
            out.append(d)
            continue
        if account_id and pg and pg != account_id:
            continue
        if contract_file:
            name = str(d.get("document_name") or "")
            if name and contract_file not in name and name not in contract_file:
                if pg and pg != account_id:
                    continue
        out.append(d)
    return out


def _drop_deprecated_when_current(docs: list[dict[str, Any]]) -> list[dict]:
    by_type: dict[str, list[dict]] = {}
    for d in docs:
        by_type.setdefault(str(d.get("document_type") or ""), []).append(d)
    out = []
    for dtype, group in by_type.items():
        statuses = {g.get("status") for g in group}
        if "current" in statuses and "deprecated" in statuses:
            out.extend(g for g in group if g.get("status") == "current")
        else:
            out.extend(group)
    return out


def resolve_evidence(
    structured_results: list[dict[str, Any]],
    retrieved_documents: list[dict[str, Any]],
    auth_account_id: str | None = None,
) -> dict[str, Any]:
    """Rank, filter, and detect conflicts between operational facts and document evidence."""
    account_id, contract_file = _account_context(structured_results)
    if not account_id and auth_account_id:
        account_id = auth_account_id
    filtered = _drop_wrong_agreements(retrieved_documents, account_id, contract_file)
    filtered = _drop_deprecated_when_current(filtered)

    conflicts: list[str] = []
    by_doc_id: dict[str, list[dict]] = {}
    for doc in filtered:
        did = doc.get("document_type") or doc.get("document_id") or ""
        by_doc_id.setdefault(str(did), []).append(doc)

    agreements = [d for d in filtered if d.get("customer_id") or d.get("postgres_account_id")]
    globals_ = [d for d in filtered if not d.get("customer_id") and not d.get("postgres_account_id")]
    if agreements and globals_:
        conflicts.append(
            "Customer agreement applies alongside global policy — agreement overrides where terms differ."
        )

    ranked = sorted(
        filtered,
        key=lambda d: (-int(d.get("authority") or 0), 0 if d.get("status") == "current" else 1),
    )

    confidence = 1.0
    if not ranked:
        confidence = 0.2
    elif conflicts:
        confidence = 0.7
    elif len(ranked) < 1 and not structured_results:
        confidence = 0.5

    return {
        "evidence": ranked,
        "conflicts": conflicts,
        "confidence": confidence,
        "structured_results": structured_results,
    }
