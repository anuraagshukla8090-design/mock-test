"""
Direct pipeline test — runs without the FastAPI server.

Uses the EXISTING MinerU outputs from test-ingestion/output/ to skip
the long MinerU processing step. Runs:
  post_processor → question_builder → LLM metadata → saves to DB

Usage:
    .venv\Scripts\python scripts\run_pipeline_direct.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

# Force UTF-8 output on Windows console
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Add project root to path ──────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.database import SessionLocal
from app.models.ingestion import Ingestion
from app.models.question import Question as QuestionModel
from app.services.ingestion_pipeline import Stage
from app.services.llm import get_llm_client
from app.services.metadata_generator import generate_metadata_batch
from app.services.post_processor import clean_content_blocks
from app.services.question_builder import build_questions
from app.services.question_builder.base import strip_latex_for_search
import shutil

# ── Known MinerU outputs from earlier test run ────────────────────────────────
MINERU_OUTPUTS = [
    {
        "filename": "chemistry.pdf",
        "content_list": ROOT / "test-ingestion/output/chemistry/chemistry_content_list.json",
        "images_dir":   ROOT / "test-ingestion/output/chemistry/images",
    },
    {
        "filename": "maths.pdf",
        "content_list": ROOT / "test-ingestion/output/maths/maths_content_list.json",
        "images_dir":   ROOT / "test-ingestion/output/maths/images",
    },
    {
        "filename": "physics.pdf",
        "content_list": ROOT / "test-ingestion/output/physics/physics_content_list.json",
        "images_dir":   ROOT / "test-ingestion/output/physics/images",
    },
]


async def run_one(entry: dict, db) -> dict:
    filename = entry["filename"]
    cl_path: Path = entry["content_list"]
    images_dir: Path = entry["images_dir"]

    print(f"\n{'-'*60}")
    print(f"  Processing: {filename}")
    print(f"  Content list: {cl_path}")

    if not cl_path.exists():
        print(f"  ✗ content_list.json not found — skipping")
        return {"filename": filename, "status": "SKIPPED", "reason": "content_list.json missing"}

    start = time.time()

    # ── 1. Create ingestion record ────────────────────────────────────────────
    ingestion_id = uuid.uuid4()
    ingestion = Ingestion(
        id=ingestion_id,
        filename=filename,
        status=Stage.MINERU_COMPLETE,   # Already have MinerU output
        mineru_output_dir=str(cl_path.parent),
    )
    db.add(ingestion)
    db.commit()
    print(f"  → Ingestion ID: {ingestion_id}")

    # ── 2. Load content list ──────────────────────────────────────────────────
    with open(cl_path, encoding="utf-8") as f:
        raw_blocks = json.load(f)
    print(f"  → Loaded {len(raw_blocks)} raw blocks")

    # ── 3. Post-process ───────────────────────────────────────────────────────
    clean_blocks = clean_content_blocks(raw_blocks)
    print(f"  → After cleaning: {len(clean_blocks)} blocks")

    ingestion.status = Stage.QUESTIONS_BUILT
    db.commit()

    # ── 4. Build questions ────────────────────────────────────────────────────
    questions, layout = build_questions(clean_blocks, images_dir)
    print(f"  → Layout detected: {layout}")
    print(f"  → Questions found: {len(questions)}")

    ingestion.questions_found = len(questions)
    ingestion.detected_layout = layout
    ingestion.detected_subjects = list({q.subject for q in questions if q.subject})
    db.commit()

    if not questions:
        ingestion.status = Stage.FAILED
        ingestion.error_message = "No questions found after building"
        db.commit()
        return {"filename": filename, "status": "FAILED", "reason": "0 questions built"}

    # ── 5. LLM metadata ───────────────────────────────────────────────────────
    print(f"  → Generating metadata for {len(questions)} questions via LLM...")
    llm = get_llm_client()
    metadata_list = await generate_metadata_batch(questions, llm, concurrency=5)
    ingestion.status = Stage.METADATA_COMPLETE
    db.commit()
    print(f"  → Metadata done")

    # ── 6. Save questions ─────────────────────────────────────────────────────
    images_dest = Path(settings.storage_dir) / "images"
    images_dest.mkdir(parents=True, exist_ok=True)

    saved = 0
    skipped = 0
    all_warnings: list[str] = []
    per_question: list[dict] = []

    for question, meta in zip(questions, metadata_list):
        q_warnings = list(question.warnings)

        q_images = []
        for img in question.images:
            src = images_dir / img["filename"]
            dst = images_dest / img["filename"]
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
            if dst.exists():
                q_images.append(img)

        options_text = " ".join((question.options or {}).values())
        raw_text = strip_latex_for_search(f"{question.stem_md} {options_text}")

        db_q = QuestionModel(
            ingestion_id=ingestion_id,
            source_pdf=filename,
            source_page=question.source_page,
            question_number=question.question_number,
            stem_md=question.stem_md,
            options=question.options or {},
            answer=question.answer,
            images=q_images,
            section_type=question.section_type,
            section_label=question.section_label,
            exam_name=meta.exam_name,
            subject=meta.subject,
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
        db.add(db_q)
        saved += 1
        per_question.append({
            "number": question.question_number,
            "status": "ok",
            "warnings": q_warnings,
        })
        all_warnings.extend(q_warnings)

    db.commit()
    elapsed = time.time() - start

    report = {
        "questions_detected": len(questions),
        "questions_stored": saved,
        "questions_skipped": skipped,
        "answers_mapped": saved,
        "images_linked": sum(len(q.images) for q in questions),
        "processing_time_s": round(elapsed, 1),
        "warnings": all_warnings,
        "errors": [],
        "per_question": per_question,
    }
    ingestion.questions_saved = saved
    ingestion.processing_time_s = elapsed
    ingestion.processing_report = report
    ingestion.status = Stage.SAVED
    db.commit()

    print(f"  [DONE] Saved {saved} questions in {elapsed:.1f}s")
    return {"filename": filename, "status": "SAVED", "report": report}


async def main():
    db = SessionLocal()
    results = []
    try:
        for entry in MINERU_OUTPUTS:
            result = await run_one(entry, db)
            results.append(result)
    finally:
        db.close()

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"\n\n{'='*60}")
    print("  FINAL RESULTS")
    print(f"{'='*60}")
    total_stored = 0
    for r in results:
        rep = r.get("report", {})
        stored = rep.get("questions_stored", 0)
        total_stored += stored
        print(f"\n  {r['filename']}")
        print(f"    Status   : {r['status']}")
        if r["status"] == "SAVED":
            print(f"    Detected : {rep.get('questions_detected')}")
            print(f"    Stored   : {stored}")
            print(f"    Images   : {rep.get('images_linked')}")
            print(f"    Time     : {rep.get('processing_time_s')}s")
            warnings = rep.get("warnings", [])
            if warnings:
                print(f"    Warnings : {len(warnings)}")
                for w in warnings[:5]:
                    print(f"      WARN: {w}")
        elif r["status"] in ("FAILED", "SKIPPED"):
            print(f"    Reason: {r.get('reason', r.get('error_message', ''))}")

    print(f"\n  TOTAL questions saved to DB: {total_stored}")
    print(f"{'='*60}\n")

    # DB stats
    from sqlalchemy import func
    new_db = SessionLocal()
    try:
        from app.models.question import Question as QM
        total = new_db.query(QM).count()
        by_subj = new_db.query(QM.subject, func.count(QM.id)).group_by(QM.subject).all()
        print(f"  DB Question Bank:")
        print(f"    Total: {total}")
        for subj, cnt in by_subj:
            print(f"    {subj or 'unknown'}: {cnt}")
    finally:
        new_db.close()


if __name__ == "__main__":
    asyncio.run(main())
