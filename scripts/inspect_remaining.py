"""Inspect remaining opts<4 questions to triage fixable vs. MinerU data loss."""
import json, pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")

# Clear cached modules
for mod_name in list(sys.modules):
    if "question_builder" in mod_name:
        del sys.modules[mod_name]

from app.services.question_builder.full_paper import FullPaperBuilder
from pathlib import Path

p = pathlib.Path(
    "C:/Users/Anurag shukla/mocktest/storage/mineru_outputs/"
    "56902aba-584d-4774-9502-6d9e8773d74a"
)
data = json.loads(list(p.rglob("*content_list*"))[0].read_text(encoding="utf-8"))

builder = FullPaperBuilder(data, Path("."))
questions = builder.build()

bad = [q for q in questions if q.section_type == "mcq" and len(q.options) < 4]
print(f"Questions with <4 opts: {[q.question_number for q in bad]}\n")


def find_q_block_range(data, q_num):
    """Return (start_idx, end_idx) of blocks belonging to question q_num."""
    start = None
    for i, b in enumerate(data):
        t = b.get("text", "")
        if re.match(rf"^\s*[Qq]\.?\s*{q_num}\s*[\.\)]", t) or re.match(rf"^\s*{q_num}\s*[\.\)]\s+\S", t):
            start = i
        elif start is not None and (
            re.match(r"^\s*[Qq]\.?\s*\d{1,3}\s*[\.\)]", t)
            or re.match(r"^\s*\d{1,3}\s*[\.\)]\s+\S", t)
        ):
            return start, i
    return start, len(data)


for q in bad:
    qn = q.question_number
    s, e = find_q_block_range(data, qn)
    print("=" * 60)
    print(f"Q{qn}  opts={q.options}")
    print(f"  warnings: {q.warnings}")
    print(f"  Blocks [{s}:{e}]:")
    for i in range(s or 0, min(e, (s or 0) + 15)):
        b = data[i]
        txt = b.get("text", "")
        print(f"    [{i:3d}] type={b['type']!r:10} | {repr(txt[:120])}")
    print()
