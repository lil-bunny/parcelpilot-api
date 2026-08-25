from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.v1 import router as v1_router
from app.core.config import settings
from app.services.hybrid_retriever import chroma_dir, warmup_store

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="ParcelPilot", version="0.1.0")
    # ponytail: MVP-UI dev server; expand via env if needed
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(v1_router, prefix="/v1")

    @app.on_event("startup")
    def _warm_chroma():
        if chroma_dir().exists():
            warmup_store()

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
