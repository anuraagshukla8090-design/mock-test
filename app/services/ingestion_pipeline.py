from __future__ import annotations
import asyncio
import logging
import shutil
import time
import uuid
from pathlib import Path
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models.ingestion import Ingestion
from app.models.question import Question as QuestionModel
from app.services.llm import get_llm_client
from app.services.metadata_generator import (
    QuestionMetadata,
    generate_metadata_batch,
)
from app.services.mineru_runner import MineruError, run_mineru
from app.services.post_processor import clean_content_blocks
from app.services.question_builder import Question, build_questions
from app.services.question_builder.base import strip_latex_for_search
logger = logging.getLogger(__name__)
# Ingestion state machine values
class Stage:
    UPLOADED          = "UPLOADED"
    MINERU_COMPLETE   = "MINERU_COMPLETE"
    QUESTIONS_BUILT   = "QUESTIONS_BUILT"
    METADATA_COMPLETE = "METADATA_COMPLETE"
    SAVED             = "SAVED"
    FAILED            = "FAILED"
def run_ingestion_sync(
    ingestion_id: uuid.UUID,
    pdf_path: Path,
) -> None:
    """
    Synchronous entry point called from FastAPI BackgroundTasks.
    Creates its own database session so there is no dependency on the
    request-scoped session (which is closed before this runs). This avoids
    the 'connection already closed' race condition that occurred when the
    request session was passed in.
    """
    db = SessionLocal()
    try:
        asyncio.run(_run_ingestion(ingestion_id, pdf_path, db))
    finally:
        db.close()
async def _run_ingestion(
    ingestion_id: uuid.UUID,
    pdf_path: Path,
    db: Session,
) -> None:
    """Full ingestion pipeline with state machine updates."""
    start_time = time.time()
    ingestion = db.get(Ingestion, ingestion_id)
    if not ingestion:
        logger.error("Ingestion %s not found in DB", ingestion_id)
        return
    # Output directory for MinerU: storage/mineru_outputs/<ingestion_id>/
    output_dir = Path(settings.storage_dir) / "mineru_outputs" / str(ingestion_id)
    try:
        # ── Stage 1: MinerU extraction ─────────────────────────────────────
        _advance(ingestion, Stage.UPLOADED, db)
        mineru_output = run_mineru(pdf_path, output_dir)
        ingestion.mineru_output_dir = str(mineru_output.output_dir)
        _advance(ingestion, Stage.MINERU_COMPLETE, db)
        # ── Stage 2: Post-process + Question Builder ───────────────────────
        clean_blocks = clean_content_blocks(mineru_output.content_list)
        # layout_type comes from the ingestion record (set at upload time)
        layout_type = ingestion.layout_type
        if not layout_type:
            raise ValueError(
                "ingestion.layout_type is not set. "
                "This ingestion was created before layout_type was required. "
                "Please re-upload with a layout_type."
            )
        questions, layout_name = build_questions(
            clean_blocks,
            mineru_output.images_dir,
            layout_type=layout_type,
        )
        ingestion.questions_found = len(questions)
        ingestion.detected_layout = layout_name
        ingestion.detected_subjects = list({
            q.subject for q in questions if q.subject
        })
        _advance(ingestion, Stage.QUESTIONS_BUILT, db)
        # ── Stage 3: LLM metadata generation ──────────────────────────────
        llm = get_llm_client()
        # For full_paper layout, subject is unknown per question — the LLM
        # identifies it from content. For all other layouts, we pass the
        # teacher-provided subject from the upload form.
        detect_subject = (layout_type == "full_paper")
        metadata_list = await generate_metadata_batch(
            questions,
            llm,
            concurrency=1,
            exam_name=ingestion.exam_name or "JEE Main",
            subject=ingestion.subject or "physics",
            detect_subject=detect_subject,
        )
        _advance(ingestion, Stage.METADATA_COMPLETE, db)
        # ── Stage 4: Copy images + save to DB ─────────────────────────────
        images_dest = Path(settings.storage_dir) / "images"
        images_dest.mkdir(parents=True, exist_ok=True)
        saved, skipped, warnings, per_question = _save_questions(
            ingestion=ingestion,
            questions=questions,
            metadata_list=metadata_list,
            images_src=mineru_output.images_dir,
            images_dest=images_dest,
            db=db,
        )
        elapsed = time.time() - start_time
        ingestion.questions_saved = saved
        ingestion.processing_time_s = elapsed
        ingestion.processing_report = {
            "questions_detected": len(questions),
            "questions_stored": saved,
            "questions_skipped": skipped,
            "answers_mapped": saved,
            "images_linked": sum(len(q.images) for q in questions),
            "processing_time_s": round(elapsed, 1),
            "warnings": warnings,
            "errors": [],
            "per_question": per_question,
        }
        _advance(ingestion, Stage.SAVED, db)
    except MineruError as exc:
        _fail(ingestion, str(exc), ingestion.status, db)
    except Exception as exc:
        _fail(ingestion, str(exc), ingestion.status, db)
    finally:
        # Clean up the temporary PDF file
        if pdf_path.exists():
            pdf_path.unlink(missing_ok=True)
def _save_questions(
    ingestion: Ingestion,
    questions: list[Question],
    metadata_list: list[QuestionMetadata],
    images_src: Path,
    images_dest: Path,
    db: Session,
) -> tuple[int, int, list[str], list[dict]]:
    """
    Write Question objects to the database and copy images to storage.
    Uses a single atomic transaction: either ALL questions are saved or
    NONE are (on DB error). Image copies that succeed before a DB failure
    are left in place (they're idempotent — same filename, same content).
    Returns (saved_count, skipped_count, warnings, per_question_report).
    """
    saved = 0
    skipped = 0
    all_warnings: list[str] = []
    per_question: list[dict] = []
    db_questions: list[QuestionModel] = []
    for question, meta in zip(questions, metadata_list):
        q_warnings = list(question.warnings)
        # Copy images from MinerU output dir to permanent storage
        q_images = []
        for img in question.images:
            src = images_src / img["filename"]
            dst = images_dest / img["filename"]
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
            if dst.exists():
                q_images.append(img)
            else:
                q_warnings.append(
                    f"Q{question.question_number}: image {img['filename']} not found"
                )
        # Build plain text for full-text search
        options_text = " ".join(meta_val for meta_val in (question.options or {}).values())
        raw_text = strip_latex_for_search(
            f"{question.stem_md} {options_text}"
        )
        db_question = QuestionModel(
            ingestion_id=ingestion.id,
            source_pdf=ingestion.filename,
            source_page=question.source_page,
            question_number=question.question_number,
            stem_md=question.stem_md,
            options=question.options or {},
            answer=question.answer,
            images=q_images,
            section_type=question.section_type,
            section_label=question.section_label,
            # exam_name comes from the ingestion record (teacher-provided).
            # subject: for full_paper layout the LLM identifies it per question;
            # for all other layouts the teacher provided it at upload time.
            exam_name=ingestion.exam_name,
            subject=meta.subject or ingestion.subject,
            chapter=meta.chapter,
            topic=meta.topic,
            subtopic=meta.subtopic,
            difficulty=meta.difficulty,
            question_type=meta.question_type,
            concepts=meta.concepts,
            has_diagram=meta.has_diagram,
            has_formula=meta.has_formula,
            llm_raw_response=meta.raw_response if meta.raw_response else None,
            raw_text=raw_text,
            status="active",
        )
        db.add(db_question)
        db_questions.append(db_question)
        saved += 1
        per_question.append({
            "number": question.question_number,
            "status": "ok",
            "warnings": q_warnings,
        })
        all_warnings.extend(q_warnings)
    # ── Atomic commit ─────────────────────────────────────────────────────────
    # If the commit fails, roll back ALL question inserts so the ingestion
    # does not leave a partial set of questions in the database.
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise RuntimeError(
            f"Failed to commit {saved} questions to the database: {exc}"
        ) from exc
    return saved, skipped, all_warnings, per_question
def _advance(ingestion: Ingestion, new_status: str, db: Session) -> None:
    ingestion.status = new_status
    db.commit()
    logger.info("Ingestion %s → %s", ingestion.id, new_status)
def _fail(
    ingestion: Ingestion,
    error_msg: str,
    failed_at: str,
    db: Session,
) -> None:
    """
    Mark ingestion as FAILED. Wraps the commit so a DB error here does not
    mask the original exception.
    """
    try:
        ingestion.status = Stage.FAILED
        ingestion.error_message = error_msg[:2000]
        ingestion.failed_at_stage = failed_at
        db.commit()
    except Exception as commit_exc:
        logger.error(
            "Ingestion %s: could not write FAILED status (%s). "
            "Original error: %s",
            ingestion.id, commit_exc, error_msg[:200],
        )
    else:
        logger.error(
            "Ingestion %s FAILED at %s: %s",
            ingestion.id, failed_at, error_msg[:200],
        )