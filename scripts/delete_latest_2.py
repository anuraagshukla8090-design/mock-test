import sys
sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")
from app.database import SessionLocal
from app.models.ingestion import Ingestion
from app.models.question import Question

db = SessionLocal()
latest_2 = db.query(Ingestion).order_by(Ingestion.created_at.desc()).limit(2).all()
for ing in latest_2:
    print(f"Deleting {ing.id} - {ing.filename}")
    db.query(Question).filter(Question.ingestion_id == ing.id).delete()
    db.delete(ing)
db.commit()
db.close()
print("Done deleting latest 2 ingestions.")
