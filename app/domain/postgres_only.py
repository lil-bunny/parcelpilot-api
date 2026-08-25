"""Detect account-metadata questions answerable from Postgres only (no vector DB)."""

from __future__ import annotations

import re

# Fields on accounts table — not in PDFs
_ACCOUNT = re.compile(
    r"\b(plan|csm|customer success|account name|premium support|what plan|who is my)\b",
    re.I,
)
# If present, user likely wants policy text from documents
_POLICY = re.compile(
    r"\b(cancellation|cancel(?:lation)?|sla|policy|service credit|credit|fee|sop|agreement terms)\b",
    re.I,
)

POSTGRES_ONLY_TOOL_HINT = (
    "Use query_operational_data(entity=account) for plan, CSM, and account metadata."
)


def is_postgres_only_question(text: str) -> bool:
    """True when the query targets DB account fields, not document policy."""
    if not (text or "").strip():
        return False
    if _POLICY.search(text):
        return False
    return bool(_ACCOUNT.search(text))
