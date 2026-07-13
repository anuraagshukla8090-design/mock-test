import sys, os, shutil
from pathlib import Path
sys.path.insert(0, r'c:\Users\Anurag shukla\mocktest')

from app.database import SessionLocal
from app.models.ingestion import Ingestion
from app.models.question import Question
from app.config import settings

def main():
    db = SessionLocal()
    try:
        latest = db.query(Ingestion).order_by(Ingestion.created_at.desc()).first()
        if not latest:
            print("No ingestions found.")
            return

        print(f"Latest ingestion: {latest.id} (File: {latest.filename})")
        
        # Delete questions associated with this ingestion
        deleted_q = db.query(Question).filter(Question.ingestion_id == latest.id).delete()
        print(f"Deleted {deleted_q} associated questions.")

        db.delete(latest)
        db.commit()
        print("Deleted ingestion record from database.")

        # Delete files
        uploads_dir = Path(settings.storage_dir) / "uploads"
        pdf_path = uploads_dir / f"{latest.id}.pdf"
        if pdf_path.exists():
            pdf_path.unlink()
            print(f"Deleted {pdf_path}")

        mineru_dir = Path(settings.storage_dir) / "mineru_outputs" / str(latest.id)
        if mineru_dir.exists():
            shutil.rmtree(mineru_dir)
            print(f"Deleted {mineru_dir}")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
