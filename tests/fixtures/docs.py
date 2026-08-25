from langchain_core.documents import Document


def chunk(
    chunk_id: str,
    *,
    authority: int,
    status: str,
    body: str,
    source: str = "doc.pdf",
    page: int = 0,
    account_id: str = "",
    postgres_account_id: str = "",
    doc_id: str = "",
) -> Document:
    return Document(
        page_content=f"[prefix]\n{body}",
        metadata={
            "chunk_id": chunk_id,
            "doc_id": doc_id or chunk_id,
            "authority": authority,
            "status": status,
            "source": source,
            "version": "v1",
            "page": page,
            "account_id": account_id,
            "postgres_account_id": postgres_account_id,
            "body": body,
            "parent": body,
        },
        id=chunk_id,
    )


SOP_CURRENT = chunk(
    "sop",
    authority=3,
    status="current",
    body="Cancellation credit if notice is 48 hours.",
    source="03_Cancellation_and_Service_Credit_SOP_v4.pdf",
    doc_id="cancellation_sop",
)
POLICY_DEPRECATED = chunk(
    "old_policy",
    authority=1,
    status="deprecated",
    body="Cancellation window is 72 hours.",
    source="02_Support_Policy_v2_DEPRECATED.pdf",
    doc_id="support_policy",
)
NORTHSTAR = chunk(
    "northstar",
    authority=4,
    status="current",
    body="Northstar agreement waives the cancellation fee.",
    source="05_Northstar_Logistics_Enterprise_Agreement.pdf",
    account_id="northstar",
    postgres_account_id="ACCT-001",
    doc_id="northstar_agreement",
)
LUMENWORKS = chunk(
    "lumenworks",
    authority=4,
    status="current",
    body="LumenWorks agreement requires 24h notice.",
    source="06_LumenWorks_Service_Agreement.pdf",
    account_id="lumenworks",
    postgres_account_id="ACCT-002",
    doc_id="lumenworks_agreement",
)
KEYWORD_ONLY = chunk(
    "keyword",
    authority=2,
    status="current",
    body="rare_token_xyz appears only in this operations note.",
    source="04_Product_Operations_Guide_and_Known_Issues.pdf",
    doc_id="product_ops",
)
SUPPORT_POLICY = chunk(
    "support_policy",
    authority=2,
    status="current",
    body="Enterprise P2 first-response target is 4 hours.",
    source="01_Support_Policy_v3_CURRENT.pdf",
    doc_id="support_policy",
)
