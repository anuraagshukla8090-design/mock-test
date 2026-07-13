"""List recent ingestions and optionally delete one by ID."""
import sys
sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")

from app.database import SessionLocal
from app.models.ingestion import Ingestion
from app.models.question import Question

db = SessionLocal()

print("=== Last 10 ingestions ===")
rows = db.query(Ingestion).order_by(Ingestion.created_at.desc()).limit(10).all()
for r in rows:
    q_count = db.query(Question).filter(Question.ingestion_id == r.id).count()
    print(f"  {r.id}  {r.status:12s}  questions={q_count}  file={r.filename}  at={str(r.created_at)[:19]}")

db.close()
