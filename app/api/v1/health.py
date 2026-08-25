from fastapi import APIRouter

from app.services.hybrid_retriever import chroma_dir

router = APIRouter()


@router.get("/health")
def health():
    path = chroma_dir()
    return {"ok": True, "chroma_ready": path.exists(), "chroma_dir": str(path)}
