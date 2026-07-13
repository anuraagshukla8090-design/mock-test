"""Inspect blocks for questions still showing opts=2."""
import json, pathlib, sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

p = pathlib.Path('C:/Users/Anurag shukla/mocktest/storage/mineru_outputs/56902aba-584d-4774-9502-6d9e8773d74a')
data = json.loads(list(p.rglob('*content_list*'))[0].read_text(encoding='utf-8'))

sys.path.insert(0, 'C:/Users/Anurag shukla/mocktest')
from app.services.question_builder.full_paper import FullPaperBuilder
from pathlib import Path

builder = FullPaperBuilder(data, Path('.'))
questions = builder.build()
q_map = {q.question_number: q for q in questions}

bad = [q for q in questions if q.section_type == 'mcq' and len(q.options) < 4]
print(f"Questions with <4 opts: {[q.question_number for q in bad]}\n")

# Find block range for each bad question by scanning forward
def find_q_blocks(data, q_num):
    """Return slice of blocks that belong to question q_num."""
    in_q = False
    result = []
    for i, b in enumerate(data):
        t = b.get('text', '')
        if re.match(rf'^\s*[Qq]\.?\s*{q_num}\s*[\.\)]', t):
            in_q = True
        elif in_q and re.match(r'^\s*[Qq]\.?\s*\d{1,3}\s*[\.\)]', t):
            break
        elif in_q and re.match(rf'^\s*{q_num+1}\s*[\.\)]\s+\S', t):
            break
        if in_q:
            result.append((i, b))
    return result

for q in bad[:5]:  # inspect first 5
    qn = q.question_number
    print(f"{'='*60}")
    print(f"Q{qn}  opts={q.options}  warnings={q.warnings}")
    blocks = find_q_blocks(data, qn)
    print(f"Blocks ({len(blocks)} found):")
    for i, b in blocks[:12]:
        print(f"  [{i}] type={b['type']!r:10} | {repr(b.get('text','')[:180])}")
    print()
