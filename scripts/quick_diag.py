"""Quick diagnostic: run builder and show first 10 questions stem + type."""
import json, pathlib, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")

for mod in list(sys.modules):
    if "question_builder" in mod:
        del sys.modules[mod]

from app.services.question_builder.full_paper import FullPaperBuilder
from pathlib import Path

p = pathlib.Path(
    "C:/Users/Anurag shukla/mocktest/storage/mineru_outputs/"
    "56902aba-584d-4774-9502-6d9e8773d74a"
)
data = json.loads(list(p.rglob("*content_list*"))[0].read_text(encoding="utf-8"))
qs = FullPaperBuilder(data, Path(".")).build()

total = len(qs)
mcq = sum(1 for q in qs if q.section_type == "mcq")
integer = sum(1 for q in qs if q.section_type == "integer")
answered = sum(1 for q in qs if q.answer)

print(f"Total: {total}  MCQ: {mcq}  Integer: {integer}  Answered: {answered}")
print()
for q in qs[:15]:
    stem_preview = q.stem_md[:60].replace("\n", " ") if q.stem_md else "EMPTY"
    print(f"Q{q.question_number:2d} [{q.section_type:7s}] opts={len(q.options)} ans={repr(q.answer)[:10]}  stem: {stem_preview}")
