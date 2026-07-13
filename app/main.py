from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.ingestion import router as ingestion_router
from app.api.natural_query import router as natural_query_router
from app.api.papers import router as papers_router
from app.api.questions import router as questions_router
from app.api.syllabus import router as syllabus_router
from app.config import settings

app = FastAPI(
    title="Question Bank & Paper Generator",
    description="AI-powered question bank and exam paper generation platform.",
    version="0.1.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# allow_origins=["*"] is fine here — this is a local dev/debug server only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(ingestion_router)
app.include_router(questions_router)
app.include_router(papers_router)
app.include_router(syllabus_router)
app.include_router(natural_query_router)

# ── Debug viewer ─────────────────────────────────────────────────────────────
# Serves question_viewer.html at http://localhost:8000/viewer
# This avoids CORS issues that occur when opening the file directly
_viewer_path = Path(__file__).parent.parent / "question_viewer.html"

@app.get("/viewer", include_in_schema=False)
def question_viewer():
    return FileResponse(str(_viewer_path), media_type="text/html")


# ── Static file serving for question images ───────────────────────────────────
images_dir = Path(settings.storage_dir) / "images"
images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/images", StaticFiles(directory=str(images_dir)), name="images")


@app.get("/health")
def health():
    """Backend health check — used by the admin panel API Debug page."""
    from app.database import SessionLocal
    from app.services.question_builder.registry import LAYOUT_REGISTRY, VALID_LAYOUT_TYPES

    # Check DB connectivity
    db_status = "connected"
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
    except Exception as exc:
        db_status = f"error: {exc}"

    # Builder registry info
    builders = {
        key: {
            "class": cls.__name__,
            "implemented": cls.__name__ not in ("WithSolutionBuilder", "FullPaperBuilder"),
        }
        for key, cls in LAYOUT_REGISTRY.items()
    }

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "version": app.version,
        "database": db_status,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "valid_layout_types": VALID_LAYOUT_TYPES,
        "builders": builders,
    }
