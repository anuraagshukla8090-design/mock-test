from __future__ import annotations
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.ingestion import Ingestion
from app.schemas.ingestion import IngestionListItem, IngestionStatusResponse
from app.services.ingestion_pipeline import Stage, run_ingestion_sync
from app.services.question_builder.registry import VALID_LAYOUT_TYPES, available_layouts
from app.config import settings
from app.constants.exams import normalize_exam_name, normalize_subject
router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])
@router.get("/layouts")
def list_layouts():
    """Return all supported layout types for the upload form dropdown."""
    return available_layouts()
@router.post("/upload", response_model=IngestionStatusResponse, status_code=202)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    exam_name: str = Form(..., description="e.g. 'JEE Main', 'NEET', 'CUET'"),
    
    subject: str = Form("", description="e.g. 'physics', 'chemistry', 'mathematics'. Leave empty for full_paper (auto-detected)."),
    layout_type: str = Form(..., description="One of: inline_answer, separate_answer_key, with_solution, full_paper"),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF for ingestion.
    Required form fields:
    - file        : PDF file
    - exam_name   : Exam identifier (free text, e.g. "JEE Main 2024 April")
    - subject     : Subject (e.g. "physics", "chemistry", "mathematics")
    - layout_type : PDF layout — determines which QuestionBuilder to use
    Returns immediately with status=UPLOADED.
    Poll GET /api/ingestion/{id}/status to track progress.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")
    # Validate layout_type
    layout_type = layout_type.strip().lower()
    if layout_type not in VALID_LAYOUT_TYPES:
        raise HTTPException(
            422,
            f"Invalid layout_type: '{layout_type}'. "
            f"Valid values: {VALID_LAYOUT_TYPES}",
        )
   
    # Validate subject — required for all layouts EXCEPT full_paper,
    # where the LLM identifies the subject per question from content.
    subject = subject.strip().lower()
    if not subject:
        
        if layout_type == "full_paper":
            subject = "mixed"  # placeholder; overridden per question by LLM
        else:
            raise HTTPException(422, "subject is required for this layout type.")
    # Normalize to canonical exam/subject names before storing.
    # e.g. "jee mains" → "JEE Main", "maths" → "mathematics"
    exam_name = normalize_exam_name(exam_name) or exam_name.strip()
    subject = normalize_subject(subject) or subject.strip()
    if not exam_name:
        raise HTTPException(422, "exam_name cannot be empty.")
    # Save PDF to uploads dir
    uploads_dir = Path(settings.storage_dir) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    ingestion_id = uuid.uuid4()
    pdf_path = uploads_dir / f"{ingestion_id}.pdf"
    contents = await file.read()
    pdf_path.write_bytes(contents)
    # Create ingestion record
    ingestion = Ingestion(
        id=ingestion_id,
        filename=file.filename,
        status=Stage.UPLOADED,
        exam_name=exam_name,
        subject=subject,
        layout_type=layout_type,
    )
    db.add(ingestion)
    db.commit()
    db.refresh(ingestion)
    # Start background processing.
    # NOTE: We do NOT pass the request db session — background tasks run in a
    # separate thread after the request has closed. run_ingestion_sync creates
    # its own session (see ingestion_pipeline.py).
    background_tasks.add_task(
        run_ingestion_sync,
        ingestion_id=ingestion_id,
        pdf_path=pdf_path,
    )
    return ingestion
@router.get("/history", response_model=list[IngestionListItem])
def list_ingestions(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all PDF uploads, newest first."""
    return (
        db.query(Ingestion)
        .order_by(Ingestion.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
@router.get("/{ingestion_id}/status", response_model=IngestionStatusResponse)
def get_ingestion_status(
    ingestion_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Get processing status for an ingestion.
    Poll every 3 seconds until status is SAVED or FAILED.
    """
    ingestion = db.get(Ingestion, ingestion_id)
    if not ingestion:
        raise HTTPException(404, f"Ingestion {ingestion_id} not found.")
    return ingestion
@router.post("/{ingestion_id}/retry", response_model=IngestionStatusResponse, status_code=202)
async def retry_ingestion(
    ingestion_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Retry a FAILED ingestion using the same exam_name, subject, and layout_type
    that were provided at upload time.
    """
    ingestion = db.get(Ingestion, ingestion_id)
    if not ingestion:
        raise HTTPException(404, f"Ingestion {ingestion_id} not found.")
    if ingestion.status not in (Stage.FAILED,):
        raise HTTPException(400, f"Can only retry FAILED ingestions. Current: {ingestion.status}")
    pdf_path = Path(settings.storage_dir) / "uploads" / f"{ingestion_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(400, "Original PDF no longer available. Please re-upload.")
    ingestion.status = Stage.UPLOADED
    ingestion.error_message = None
    ingestion.failed_at_stage = None
    db.commit()
    background_tasks.add_task(
        run_ingestion_sync,
        ingestion_id=ingestion_id,
        pdf_path=pdf_path,
    )
    return ingestion


@router.delete("/{ingestion_id}", status_code=204)
def delete_ingestion(
    ingestion_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Hard-delete an ingestion and ALL its associated data:
    - All questions extracted from this PDF (CASCADE via FK, but explicit here)
    - The ingestion DB record
    - The uploaded PDF file from storage/uploads/
    - The MinerU output directory from storage/mineru_outputs/

    This is irreversible.
    """
    from app.models.question import Question

    ingestion = db.get(Ingestion, ingestion_id)
    if not ingestion:
        raise HTTPException(404, f"Ingestion {ingestion_id} not found.")

    # Delete all questions from this ingestion first
    db.query(Question).filter(Question.ingestion_id == ingestion_id).delete()

    # Delete the ingestion record (CASCADE handles PaperQuestion refs)
    db.delete(ingestion)
    db.commit()

    # Clean up files (best-effort — don't fail if already missing)
    import shutil
    pdf_path = Path(settings.storage_dir) / "uploads" / f"{ingestion_id}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()

    mineru_dir = Path(settings.storage_dir) / "mineru_outputs" / str(ingestion_id)
    if mineru_dir.exists():
        shutil.rmtree(mineru_dir, ignore_errors=True)