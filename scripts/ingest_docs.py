"""Index artifacts/*.pdf into Chroma. Fails clearly if the pack is missing."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pypdf
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.integrations.llm.client import get_embeddings
from app.services.hybrid_retriever import COLLECTION, chroma_dir

ARTIFACTS_DIR = ROOT / "artifacts"
CATALOG_PATH = ARTIFACTS_DIR / "catalog.json"
EXPECTED = (
    "01_Support_Policy_v3_CURRENT.pdf, "
    "02_Support_Policy_v2_DEPRECATED.pdf, "
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf, "
    "04_Product_Operations_Guide_and_Known_Issues.pdf, "
    "05_Northstar_Logistics_Enterprise_Agreement.pdf, "
    "06_LumenWorks_Service_Agreement.pdf"
)
_SPLITTER = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", ". ", " "],
    chunk_size=400,
    chunk_overlap=80,
    add_start_index=True,
)


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def catalog_for(filename: str, catalog: dict) -> dict | None:
    if filename in catalog:
        return catalog[filename]
    for key, meta in catalog.items():
        if key in filename or filename in key:
            return meta
    return None


def context_prefix(meta: dict, page: int) -> str:
    account = meta.get("account_id") or "global"
    return (
        f"[{meta['doc_id']} | {meta['version']} | {meta['status']} "
        f"| page {page} | account={account}]"
    )


def chunk_page(page_doc: Document) -> list[Document]:
    children = _SPLITTER.split_documents([page_doc])
    meta = page_doc.metadata
    page = int(meta.get("page", 0))
    prefix = context_prefix(meta, page)
    parent = page_doc.page_content
    out = []
    for i, child in enumerate(children):
        body = child.page_content
        child_meta = {
            **{k: ("" if v is None else v) for k, v in meta.items()},
            "body": body,
            "parent": parent,
            "chunk": i,
        }
        cid = f"{meta.get('source', 'doc')}::p{page}::c{i}"
        child_meta["chunk_id"] = cid
        out.append(Document(page_content=f"{prefix}\n{body}", metadata=child_meta, id=cid))
    return out


def load_pdf_pages(path: Path, meta: dict) -> list[Document]:
    reader = pypdf.PdfReader(str(path))
    docs = []
    for i, page in enumerate(reader.pages):
        docs.append(
            Document(
                page_content=page.extract_text() or "",
                metadata={
                    "source": path.name,
                    "page": i,
                    "doc_id": meta["doc_id"],
                    "version": meta["version"],
                    "status": meta["status"],
                    "authority": int(meta["authority"]),
                    "account_id": meta.get("account_id") or "",
                },
            )
        )
    return docs


def main() -> int:
    pdfs = sorted(ARTIFACTS_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"drop the six pack PDFs into artifacts/ (expected: {EXPECTED})", file=sys.stderr)
        return 1
    catalog = load_catalog()
    children: list[Document] = []
    for path in pdfs:
        meta = catalog_for(path.name, catalog)
        if meta is None:
            print(f"unknown file (not in catalog.json): {path.name}", file=sys.stderr)
            return 1
        for page_doc in load_pdf_pages(path, meta):
            children.extend(chunk_page(page_doc))
    out_dir = chroma_dir()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    settings.apply_env()
    if not settings.llm_api_key:
        print("Set OPENAI_API_KEY in .env before ingest.", file=sys.stderr)
        return 1
    embeddings = get_embeddings()
    store = Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings,
        persist_directory=str(out_dir),
    )
    ids = [c.metadata["chunk_id"] for c in children]
    store.add_documents(documents=children, ids=ids)
    print(f"Indexed {len(children)} chunks from {len(pdfs)} PDFs -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
