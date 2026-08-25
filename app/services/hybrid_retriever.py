"""Hybrid retrieve: Chroma (dense) ∪ BM25 (keyword), then authority sort. No class hierarchy."""

from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

if TYPE_CHECKING:
    from langchain_chroma import Chroma

ROOT = Path(__file__).resolve().parents[2]
COLLECTION = "parcelpilot_docs"


def chroma_dir() -> Path:
    from app.core.config import settings

    if settings.chroma_dir.strip():
        return Path(settings.chroma_dir)
    return ROOT / "data" / "chroma"

_chroma: Chroma | None = None
_bm25_docs: list[Document] = []
_bm25: BM25Okapi | None = None
_store_lock = threading.Lock()

AGREEMENT_DOC_IDS = frozenset({"northstar_agreement", "lumenworks_agreement"})


def _status_rank(status: str) -> int:
    return 0 if status == "current" else 1


def merge_and_rank(chroma_hits: list[Document], bm25_hits: list[Document], k: int = 6) -> list[Document]:
    by_id: dict[str, Document] = {}
    for doc in chroma_hits + bm25_hits:
        cid = doc.metadata.get("chunk_id") or doc.id or doc.page_content[:40]
        if cid not in by_id:
            by_id[cid] = doc
    ranked = sorted(
        by_id.values(),
        key=lambda d: (
            -int(d.metadata.get("authority") or 0),
            _status_rank(str(d.metadata.get("status") or "")),
        ),
    )
    return ranked[:k]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def _norm(s: str) -> str:
    return s.strip().lower().replace(" ", "_")


def doc_matches_filters(meta: dict, filters: dict | None) -> bool:
    """True if document metadata passes all filter keys (empty filters → True)."""
    if not filters:
        return True
    m = meta or {}
    if filters.get("status") and m.get("status") != filters["status"]:
        return False
    if filters.get("document_type") and m.get("doc_id") != filters["document_type"]:
        return False
    if filters.get("document_name"):
        want = _norm(str(filters["document_name"]))
        source = _norm(str(m.get("source") or ""))
        if want not in source and source not in want:
            return False
    acct_pg = (m.get("postgres_account_id") or "").upper()
    if filters.get("customer_account_id"):
        if acct_pg != str(filters["customer_account_id"]).upper():
            return False
    elif filters.get("customer_id"):
        cid = _norm(str(filters["customer_id"]))
        slug = _norm(str(m.get("account_id") or ""))
        if slug and slug != cid and cid not in slug:
            return False
    return True


def _filter_docs(docs: list[Document], filters: dict | None) -> list[Document]:
    if not filters:
        return docs
    return [d for d in docs if doc_matches_filters(d.metadata, filters)]


def _load_store():
    global _chroma, _bm25, _bm25_docs
    if _chroma is not None:
        return
    with _store_lock:
        if _chroma is not None:
            return
        from langchain_chroma import Chroma

        from app.integrations.llm.client import get_embeddings

        _chroma = Chroma(
            collection_name=COLLECTION,
            embedding_function=get_embeddings(),
            persist_directory=str(chroma_dir()),
        )
        raw = _chroma.get(include=["documents", "metadatas"])
        _bm25_docs = [
            Document(page_content=text or "", metadata=meta or {}, id=(meta or {}).get("chunk_id"))
            for text, meta in zip(raw.get("documents") or [], raw.get("metadatas") or [])
        ]
        if _bm25_docs:
            _bm25 = BM25Okapi([_tokenize(d.page_content) for d in _bm25_docs])


def warmup_store() -> None:
    """Load Chroma on the main thread (startup)."""
    _load_store()


def search(query: str, k: int = 6, filters: dict | None = None) -> list[Document]:
    _load_store()
    chroma = _chroma
    bm25 = _bm25
    docs = _bm25_docs
    if not docs or chroma is None or bm25 is None:
        return []

    pool = _filter_docs(docs, filters) if filters else docs
    if filters and not pool:
        return []

    fetch_k = max(k * 2, k)
    chroma_hits = chroma.similarity_search(query, k=fetch_k)
    chroma_hits = _filter_docs(chroma_hits, filters) if filters else chroma_hits

    if pool:
        pool_set = {d.metadata.get("chunk_id") for d in pool}
        scores = bm25.get_scores(_tokenize(query))
        top = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)
        bm25_hits = [docs[i] for i in top if scores[i] > 0 and docs[i].metadata.get("chunk_id") in pool_set][
            :fetch_k
        ]
    else:
        scores = bm25.get_scores(_tokenize(query))
        top = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:fetch_k]
        bm25_hits = [docs[i] for i in top if scores[i] > 0]

    merged = merge_and_rank(chroma_hits, bm25_hits, k=fetch_k)
    if filters:
        merged = _filter_docs(merged, filters)
    return merged[:k]


def to_evidence(docs: list[Document]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for doc in docs:
        m = doc.metadata
        parent_key = f"{m.get('source')}::{m.get('page')}"
        if parent_key in seen:
            continue
        seen.add(parent_key)
        text = m.get("parent") or m.get("body") or doc.page_content
        out.append(
            {
                "document_id": m.get("doc_id") or m.get("source"),
                "document_name": m.get("source"),
                "document_type": m.get("doc_id"),
                "page": m.get("page"),
                "section": m.get("chunk"),
                "text": text,
                "status": m.get("status"),
                "authority": m.get("authority"),
                "customer_id": m.get("account_id") or None,
                "postgres_account_id": m.get("postgres_account_id") or None,
                "score": None,
            }
        )
    return out


def format_hits(docs: list[Document]) -> str:
    if not docs:
        return (
            "No indexed documents. Drop PDFs into artifacts/ then run: "
            "uv run python scripts/ingest_docs.py"
        )
    seen_parents: set[str] = set()
    parts = []
    for doc in docs:
        m = doc.metadata
        parent_key = f"{m.get('source')}::{m.get('page')}"
        if parent_key in seen_parents:
            continue
        seen_parents.add(parent_key)
        body = m.get("parent") or m.get("body") or doc.page_content
        parts.append(
            f"source={m.get('source')} version={m.get('version')} "
            f"status={m.get('status')} authority={m.get('authority')} "
            f"account={m.get('account_id') or 'global'} page={m.get('page')}\n{body}"
        )
    return "\n\n---\n\n".join(parts)
