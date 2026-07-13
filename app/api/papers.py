from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.paper import Paper, PaperQuestion
from app.models.question import Question
from app.schemas.paper import (
    AddQuestionRequest,
    AlternativesResponse,
    ApproveRequest,
    GeneratePaperRequest,
    PaperListItem,
    PaperResponse,
    SwapQuestionRequest,
)
from app.schemas.question import QuestionResponse
from app.services.paper_generator import (
    build_export_markdown,
    create_draft,
    generate_blueprint,
    regenerate_draft,
    shuffle_draft,
)
from app.services.question_selector import (
    PaperBlueprint,
    get_alternatives,
    select_questions,
)

router = APIRouter(prefix="/api/papers", tags=["papers"])


def _get_paper_or_404(paper_id: uuid.UUID, db: Session) -> Paper:
    paper = (
        db.query(Paper)
        .options(
            joinedload(Paper.questions).joinedload(PaperQuestion.question)
        )
        .filter(Paper.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(404, f"Paper {paper_id} not found.")
    return paper


@router.post("/generate", response_model=PaperResponse, status_code=201)
async def generate_paper(
    request: GeneratePaperRequest,
    db: Session = Depends(get_db),
):
    """
    Convert natural language prompt → blueprint → select questions → create draft.
    The teacher MUST review and approve before the paper becomes final.
    """
    blueprint = await generate_blueprint(request.prompt)
    selected = select_questions(blueprint, db)

    if not selected:
        raise HTTPException(
            422,
            f"No questions found matching: subject={blueprint.subject}, "
            f"chapters={blueprint.chapters}. "
            "Ingest more PDFs for this subject first."
        )

    paper = create_draft(request.prompt, blueprint, selected, db)
    return _get_paper_or_404(paper.id, db)


@router.get("", response_model=list[PaperListItem])
def list_papers(
    status: str | None = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List all papers, newest first."""
    q = db.query(Paper)
    if status:
        q = q.filter(Paper.status == status)
    return q.order_by(Paper.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(paper_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get full paper draft with all question details."""
    return _get_paper_or_404(paper_id, db)


@router.patch("/{paper_id}/questions/{pq_id}", response_model=PaperResponse)
def swap_question(
    paper_id: uuid.UUID,
    pq_id: uuid.UUID,
    request: SwapQuestionRequest,
    db: Session = Depends(get_db),
):
    """Replace one question with another. The new question must exist and not already be in the paper."""
    paper = _get_paper_or_404(paper_id, db)
    if paper.status == "approved":
        raise HTTPException(400, "Cannot edit an approved paper.")

    pq = db.get(PaperQuestion, pq_id)
    if not pq or pq.paper_id != paper_id:
        raise HTTPException(404, f"PaperQuestion {pq_id} not found in paper {paper_id}.")

    new_q = db.get(Question, request.new_question_id)
    if not new_q:
        raise HTTPException(404, f"Question {request.new_question_id} not found.")

    # Check not already in paper
    existing_ids = {pq.question_id for pq in paper.questions}
    if request.new_question_id in existing_ids:
        raise HTTPException(400, "This question is already in the paper.")

    pq.question_id = request.new_question_id
    db.commit()
    return _get_paper_or_404(paper_id, db)


@router.delete("/{paper_id}/questions/{pq_id}", response_model=PaperResponse)
def remove_question(
    paper_id: uuid.UUID,
    pq_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Remove a question from a draft paper. Renumbers remaining questions."""
    paper = _get_paper_or_404(paper_id, db)
    if paper.status == "approved":
        raise HTTPException(400, "Cannot edit an approved paper.")

    pq = db.get(PaperQuestion, pq_id)
    if not pq or pq.paper_id != paper_id:
        raise HTTPException(404, f"PaperQuestion {pq_id} not found.")

    removed_position = pq.position
    db.delete(pq)
    db.flush()

    # Shift positions down for all items after the removed one
    remaining = (
        db.query(PaperQuestion)
        .filter(
            PaperQuestion.paper_id == paper_id,
            PaperQuestion.position > removed_position,
        )
        .all()
    )
    for remaining_pq in remaining:
        remaining_pq.position -= 1
        remaining_pq.display_number = remaining_pq.position

    db.commit()
    return _get_paper_or_404(paper_id, db)


@router.post("/{paper_id}/questions", response_model=PaperResponse, status_code=201)
def add_question(
    paper_id: uuid.UUID,
    request: AddQuestionRequest,
    db: Session = Depends(get_db),
):
    """Add a specific question to a draft paper at a given position (or end)."""
    paper = _get_paper_or_404(paper_id, db)
    if paper.status == "approved":
        raise HTTPException(400, "Cannot edit an approved paper.")

    new_q = db.get(Question, request.question_id)
    if not new_q:
        raise HTTPException(404, f"Question {request.question_id} not found.")

    existing_ids = {pq.question_id for pq in paper.questions}
    if request.question_id in existing_ids:
        raise HTTPException(400, "This question is already in the paper.")

    # Determine insert position
    max_position = max((pq.position for pq in paper.questions), default=0)
    insert_at = request.position if request.position else max_position + 1
    insert_at = min(insert_at, max_position + 1)

    # Shift existing positions up
    to_shift = (
        db.query(PaperQuestion)
        .filter(
            PaperQuestion.paper_id == paper_id,
            PaperQuestion.position >= insert_at,
        )
        .all()
    )
    for pq in to_shift:
        pq.position += 1
        pq.display_number = pq.position

    section = request.paper_section or (
        "Section A" if new_q.section_type == "mcq" else "Section B"
    )
    new_pq = PaperQuestion(
        paper_id=paper_id,
        question_id=request.question_id,
        position=insert_at,
        paper_section=section,
        display_number=insert_at,
        locked=False,
    )
    db.add(new_pq)
    db.commit()
    return _get_paper_or_404(paper_id, db)


@router.patch("/{paper_id}/shuffle", response_model=PaperResponse)
def shuffle_paper(
    paper_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Shuffle unlocked questions within each section. Locked questions keep their position."""
    paper = _get_paper_or_404(paper_id, db)
    if paper.status == "approved":
        raise HTTPException(400, "Cannot shuffle an approved paper.")
    return shuffle_draft(paper, db)


@router.patch("/{paper_id}/questions/{pq_id}/lock", response_model=PaperResponse)
def toggle_lock(
    paper_id: uuid.UUID,
    pq_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Toggle the locked state of a question in the draft."""
    paper = _get_paper_or_404(paper_id, db)
    if paper.status == "approved":
        raise HTTPException(400, "Cannot edit an approved paper.")

    pq = db.get(PaperQuestion, pq_id)
    if not pq or pq.paper_id != paper_id:
        raise HTTPException(404, f"PaperQuestion {pq_id} not found.")

    pq.locked = not pq.locked
    db.commit()
    return _get_paper_or_404(paper_id, db)


@router.get("/{paper_id}/questions/{pq_id}/alternatives", response_model=AlternativesResponse)
def get_alternatives_for_question(
    paper_id: uuid.UUID,
    pq_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Get 3 alternative questions with the same chapter and difficulty,
    not already in this paper.
    """
    paper = _get_paper_or_404(paper_id, db)
    pq = db.get(PaperQuestion, pq_id)
    if not pq or pq.paper_id != paper_id:
        raise HTTPException(404, f"PaperQuestion {pq_id} not found.")

    existing_ids = [pq.question_id for pq in paper.questions]
    ref_question = db.get(Question, pq.question_id)

    alternatives = get_alternatives(
        paper_question_id_to_exclude=existing_ids,
        reference_question=ref_question,
        db=db,
        count=3,
    )
    return AlternativesResponse(alternatives=alternatives)


@router.post("/{paper_id}/approve", response_model=PaperResponse)
def approve_paper(
    paper_id: uuid.UUID,
    request: ApproveRequest,
    db: Session = Depends(get_db),
):
    """
    Approve a draft paper. This is the only path to 'approved' status.
    No auto-approve exists — teacher must always call this endpoint.
    """
    paper = _get_paper_or_404(paper_id, db)
    if paper.status == "approved":
        raise HTTPException(400, "Paper is already approved.")
    if paper.status != "draft":
        raise HTTPException(400, f"Cannot approve a paper with status: {paper.status}")

    paper.status = "approved"
    if request.notes:
        paper.notes = request.notes
    db.commit()
    return _get_paper_or_404(paper_id, db)


@router.post("/{paper_id}/regenerate", response_model=PaperResponse)
async def regenerate_paper(
    paper_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Regenerate a draft with a new random seed.
    Same blueprint, different question selection.
    The teacher can call this as many times as needed before approving.
    """
    paper = _get_paper_or_404(paper_id, db)
    if paper.status == "approved":
        raise HTTPException(400, "Cannot regenerate an approved paper.")

    blueprint_data = paper.blueprint
    blueprint = PaperBlueprint(
        exam_name=blueprint_data["exam_name"],
        subject=blueprint_data["subject"],
        total_questions=blueprint_data["total_questions"],
        section_a_count=blueprint_data["section_a_count"],
        section_b_count=blueprint_data["section_b_count"],
        chapters=blueprint_data["chapters"],
        difficulty_distribution=blueprint_data["difficulty_distribution"],
        type_distribution=blueprint_data["type_distribution"],
        seed=__import__("random").randint(1, 2**31),  # New seed
    )

    selected = select_questions(blueprint, db)
    if not selected:
        raise HTTPException(422, "No questions found. Cannot regenerate.")

    updated_paper = regenerate_draft(paper, paper.prompt, blueprint, selected, db)
    return _get_paper_or_404(updated_paper.id, db)


@router.get("/{paper_id}/export", response_class=PlainTextResponse)
def export_paper(
    paper_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Export an approved paper as formatted Markdown.
    Only approved papers can be exported.
    """
    paper = _get_paper_or_404(paper_id, db)
    if paper.status != "approved":
        raise HTTPException(400, "Only approved papers can be exported.")
    return build_export_markdown(paper)
