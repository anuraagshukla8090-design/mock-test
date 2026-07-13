import sys, json, re
sys.path.append(r'c:\Users\Anurag shukla\mocktest')
from app.database import SessionLocal
from app.models.ingestion import Ingestion

db = SessionLocal()
latest_ingestion = db.query(Ingestion).order_by(Ingestion.created_at.desc()).first()

cl_path = r'C:\Users\Anurag shukla\mocktest\storage\mineru_outputs\\' + str(latest_ingestion.id) + '\\' + str(latest_ingestion.id) + '\\' + str(latest_ingestion.id) + '_content_list.json'
with open(cl_path, 'r', encoding='utf-8') as f:
    blocks = json.load(f)

for i, b in enumerate(blocks):
    if b.get('type') == 'text' and '54. Consider' in b.get('text', ''):
        print('Found Q54 start at index', i)
        for j in range(i, i+10):
            if j < len(blocks):
                print(f"Block {j}: type={blocks[j].get('type')} text/img={blocks[j].get('text') or blocks[j].get('img_path')}")
        break

for i, b in enumerate(blocks):
    if b.get('type') == 'text' and '62. Match List-I' in b.get('text', ''):
        print('\nFound Q62 start at index', i)
        for j in range(i, i+10):
            if j < len(blocks):
                print(f"Block {j}: type={blocks[j].get('type')} text/img={blocks[j].get('text') or blocks[j].get('img_path')}")
        break
