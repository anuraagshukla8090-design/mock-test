from __future__ import annotations

import random
import uuid

from sqlalchemy.orm import Session

from app.models.paper import Paper, PaperQuestion
from app.models.question import Question
from app.services.llm import get_llm_client
from app.services.question_selector import PaperBlueprint, select_questions

_BLUEPRINT_PROMPT = """You are a paper structure planner for Indian competitive exams.

Teacher's request: "{prompt}"

Convert this into a structured paper blueprint. Return ONLY a JSON object:

{{
  "exam_name": "JEE Main",
  "subject": "physics",
  "total_questions": 30,
  "section_a_count": 20,
  "section_b_count": 10,
  "chapters": ["Kinematics", "Laws of Motion", "Rotational Motion"],
  "difficulty_distribution": {{"easy": 0.2, "medium": 0.6, "hard": 0.2}},
  "type_distribution": {{"conceptual": 0.6, "numerical": 0.4}},
  "special_instructions": null
}}

Rules:
- Use standard NCERT chapter names.
- "till Rotational Motion" means all chapters up to and including Rotational Motion.
- Default difficulty if not specified: {{"easy": 0.2, "medium": 0.5, "hard": 0.3}}.
- JEE Main default: section_a_count=20 (MCQ), section_b_count=10 (integer).
- NEET default: total 180 questions across 4 subjects — adjust per subject.
- difficulty_distribution values must sum to 1.0.
- type_distribution values must sum to 1.0.
- Return ONLY the JSON object. No explanation."""


async def generate_blueprint(prompt: str) -> PaperBlueprint:
    """Call LLM to convert natural language prompt into a PaperBlueprint."""
    llm = get_llm_client()
    filled_prompt = _BLUEPRINT_PROMPT.format(prompt=prompt)
    raw = await llm.generate_json(filled_prompt)

    seed = random.randint(1, 2**31)

    return PaperBlueprint(
        exam_name=raw.get("exam_name", "JEE Main"),
        subject=raw.get("subject", "physics"),
        total_questions=int(raw.get("total_questions", 30)),
        section_a_count=int(raw.get("section_a_count", 20)),
        section_b_count=int(raw.get("section_b_count", 10)),
        chapters=raw.get("chapters", []),
        difficulty_distribution=raw.get(
            "difficulty_distribution", {"easy": 0.2, "medium": 0.5, "hard": 0.3}
        ),
        type_distribution=raw.get(
            "type_distribution", {"conceptual": 0.5, "numerical": 0.5}
        ),
        seed=seed,
        special_instructions=raw.get("special_instructions"),
    )


def create_draft(
    prompt: str,
    blueprint: PaperBlueprint,
    selected_questions: list[Question],
    db: Session,
) -> Paper:
    """
    Create a Paper in 'draft' status from selected questions.
    Assigns position and display_number to each PaperQuestion.
    Section A questions come first, then Section B.
    """
    paper = Paper(
        prompt=prompt,
        blueprint={
            "exam_name": blueprint.exam_name,
            "subject": blueprint.subject,
            "total_questions": blueprint.total_questions,
            "section_a_count": blueprint.section_a_count,
            "section_b_count": blueprint.section_b_count,
            "chapters": blueprint.chapters,
            "difficulty_distribution": blueprint.difficulty_distribution,
            "type_distribution": blueprint.type_distribution,
            "seed": blueprint.seed,
            "special_instructions": blueprint.special_instructions,
        },
        status="draft",
    )
    db.add(paper)
    db.flush()  # Get paper.id without committing

    # Split into sections
    mcq_qs = [q for q in selected_questions if q.section_type == "mcq"]
    int_qs = [q for q in selected_questions if q.section_type == "integer"]
    ordered = mcq_qs + int_qs

    for i, question in enumerate(ordered, start=1):
        section = "Section A" if question.section_type == "mcq" else "Section B"
        pq = PaperQuestion(
            paper_id=paper.id,
            question_id=question.id,
            position=i,
            paper_section=section,
            display_number=i,
            locked=False,
        )
        db.add(pq)

    db.commit()
    db.refresh(paper)
    return paper


def shuffle_draft(paper: Paper, db: Session) -> Paper:
    """
    Shuffle unlocked questions within each section, preserving locked positions.
    Section A and Section B are shuffled independently.
    """
    all_pqs = sorted(paper.questions, key=lambda pq: pq.position)

    section_a = [pq for pq in all_pqs if pq.paper_section == "Section A"]
    section_b = [pq for pq in all_pqs if pq.paper_section == "Section B"]

    def _shuffle_section(pqs: list[PaperQuestion]) -> None:
        locked = [(pq.position, pq) for pq in pqs if pq.locked]
        unlocked = [pq for pq in pqs if not pq.locked]
        random.shuffle(unlocked)

        # Re-assign positions: locked stay, unlocked fill the gaps
        locked_positions = {pos for pos, _ in locked}
        all_positions = [pq.position for pq in pqs]
        free_positions = sorted(p for p in all_positions if p not in locked_positions)

        for pq, pos in zip(unlocked, free_positions):
            pq.position = pos

    _shuffle_section(section_a)
    _shuffle_section(section_b)

    # Recompute display_number
    all_pqs_sorted = sorted(paper.questions, key=lambda pq: pq.position)
    for i, pq in enumerate(all_pqs_sorted, start=1):
        pq.display_number = i

    db.commit()
    db.refresh(paper)
    return paper


def regenerate_draft(paper: Paper, prompt: str, blueprint: PaperBlueprint,
                     selected_questions: list[Question], db: Session) -> Paper:
    """
    Replace an existing draft's questions with a new selection.
    Keeps the same paper ID. New seed in blueprint ensures different selection.
    """
    # Delete existing paper_questions
    for pq in list(paper.questions):
        db.delete(pq)
    db.flush()

    # Update blueprint with new seed
    paper.prompt = prompt
    paper.blueprint = {
        **paper.blueprint,
        "seed": blueprint.seed,
        "chapters": blueprint.chapters,
        "difficulty_distribution": blueprint.difficulty_distribution,
    }

    # Re-add questions
    mcq_qs = [q for q in selected_questions if q.section_type == "mcq"]
    int_qs = [q for q in selected_questions if q.section_type == "integer"]
    ordered = mcq_qs + int_qs

    for i, question in enumerate(ordered, start=1):
        section = "Section A" if question.section_type == "mcq" else "Section B"
        pq = PaperQuestion(
            paper_id=paper.id,
            question_id=question.id,
            position=i,
            paper_section=section,
            display_number=i,
            locked=False,
        )
        db.add(pq)

    db.commit()
    db.refresh(paper)
    return paper


def build_export_markdown(paper: Paper) -> str:
    """
    Generate the final formatted markdown for an approved paper.
    Ordered by position. Sections labeled.
    """
    lines: list[str] = []
    current_section: str | None = None

    pqs = sorted(paper.questions, key=lambda pq: pq.position)

    for pq in pqs:
        q = pq.question

        if pq.paper_section != current_section:
            current_section = pq.paper_section
            lines.append(f"\n## {current_section}\n")

        lines.append(f"**Q{pq.display_number}.** {q.stem_md}\n")

        if q.options:
            for key, val in q.options.items():
                lines.append(f"({key}) {val}  ")
            lines.append("")

        for img in q.images:
            lines.append(f"![diagram](images/{img['filename']})\n")

    return "\n".join(lines)
