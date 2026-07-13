"""Delete an ingestion and all its questions (CASCADE)."""
import sys
sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")

import uuid
from app.database import SessionLocal
from app.models.ingestion import Ingestion
from app.models.question import Question

# ← ID to delete (the polluted one)
TARGET_ID = uuid.UUID("35e51914-678e-46e4-9bff-7c7de6b18e7f")

db = SessionLocal()
ingestion = db.get(Ingestion, TARGET_ID)

if not ingestion:
    print(f"Ingestion {TARGET_ID} not found.")
    db.close()
    sys.exit(1)

q_count = db.query(Question).filter(Question.ingestion_id == TARGET_ID).count()
print(f"About to delete: {ingestion.filename}")
print(f"  Status    : {ingestion.status}")
print(f"  Questions : {q_count}")
print(f"  Created   : {ingestion.created_at}")
print()

# Questions cascade-delete because of ForeignKey(..., ondelete="CASCADE")
# But SQLAlchemy ORM needs explicit delete of children first unless
# cascade="all, delete-orphan" is on the relationship.
# Safe approach: delete questions first, then ingestion.
deleted_q = db.query(Question).filter(Question.ingestion_id == TARGET_ID).delete()
db.delete(ingestion)
db.commit()
db.close()

print(f"Deleted {deleted_q} questions and ingestion record.")
print("Done.")
