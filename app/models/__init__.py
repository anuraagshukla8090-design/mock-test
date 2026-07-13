"""
Import all models here so Alembic's autogenerate can discover them,
and so Base.metadata has the full schema when create_all() is called.
"""
from app.models.ingestion import Ingestion  # noqa: F401
from app.models.paper import Paper, PaperQuestion  # noqa: F401
from app.models.question import Question  # noqa: F401
from app.models.syllabus import Syllabus  # noqa: F401

__all__ = ["Ingestion", "Question", "Paper", "PaperQuestion", "Syllabus"]
