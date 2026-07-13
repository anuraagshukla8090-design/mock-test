"""
Natural Query API — syllabus-aware paper generation.

POST /api/papers/syllabus-query

Accepts a natural language prompt, runs the full pipeline, and returns:
  - Candidate preview (counts + 5 sample questions)
  - Draft paper (if enough questions exist)

The draft paper uses the existing paper workflow — teacher reviews and
approves via the existing PATCH/POST /api/papers/{id}/approve endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.natural_query.exceptions import (
    BlueprintValidationError,
    ChapterNotFoundError,
    EmptyRangeError,
    NaturalQueryParseError,
    SyllabusNotFoundError,
)
from app.services.natural_query.pipeline import SyllabusQueryPipeline
from app.services.natural_query.schemas import (
    SyllabusQueryRequest,
    SyllabusQueryResponse,
)

router = APIRouter(prefix="/api/papers", tags=["natural-query"])

# One pipeline instance per process (stateless — safe to reuse)
_pipeline = SyllabusQueryPipeline()


@router.post("/syllabus-query", response_model=SyllabusQueryResponse, status_code=201)
async def syllabus_query(
    request: SyllabusQueryRequest,
    db: Session = Depends(get_db),
):
    """
    Natural language → syllabus-aware question selection → draft paper.

    ## Pipeline
    1. LLM extracts intent (chapter mode, filters) from the prompt
    2. Validator checks field consistency
    3. SyllabusResolver expands chapter range deterministically (no LLM)
    4. SQL filters built from resolved chapters + extra filters
    5. Candidate preview computed (counts + 5 samples)
    6. If enough questions: QuestionSelector picks, Draft Paper created
    7. If not enough: returns preview with `can_generate=false`, `paper_id=null`

    ## Chapter filter modes
    - **upto**: "till Rotational Motion" → chapters 1–N
    - **after**: "after Thermodynamics" → chapters N+1 to end
    - **between**: "from Matrices to Determinants" → chapters M–N
    - **from**: "from Electrostatics onwards" → chapters N to end
    - **exact**: "only from Kinematics" → single chapter

    ## Extra filters
    `difficulty`, `question_type`, `section_type`, `has_formula`,
    `has_diagram`, `concepts` (OR semantics in V1)

    ## Exclusions
    "till Rotational Motion but exclude Kinematics" →
    `exclude_chapters: ["Kinematics"]`
    """
    try:
        result = await _pipeline.run(prompt=request.prompt, db=db)
    except NaturalQueryParseError as exc:
        raise HTTPException(422, detail=exc.user_message)
    except BlueprintValidationError as exc:
        raise HTTPException(422, detail=exc.user_message)
    except SyllabusNotFoundError as exc:
        raise HTTPException(422, detail=exc.user_message)
    except ChapterNotFoundError as exc:
        raise HTTPException(
            422,
            detail={
                "message": exc.user_message,
                "chapter_name": exc.chapter_name,
                "suggestions": exc.suggestions,
            },
        )
    except EmptyRangeError as exc:
        raise HTTPException(422, detail=exc.user_message)
    except Exception as exc:
        # Unexpected error — re-raise as 500 for FastAPI's default handler
        raise HTTPException(500, detail=f"Pipeline error: {exc}") from exc

    # When can_generate is False, return 200 (not 201 — no resource was created)
    if not result.candidates.can_generate:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=200,
            content=result.model_dump(mode="json"),
        )

    return result
