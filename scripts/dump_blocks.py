"""Dump full content_list for architectural analysis."""
import json, pathlib, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = pathlib.Path(
    "C:/Users/Anurag shukla/mocktest/storage/mineru_outputs/"
    "56902aba-584d-4774-9502-6d9e8773d74a"
)
data = json.loads(list(p.rglob("*content_list*"))[0].read_text(encoding="utf-8"))

print(f"Total blocks: {len(data)}\n")
for i, b in enumerate(data):
    t = b.get("text", "")[:100].replace("\n", "↵")
    extra = ""
    if b.get("type") == "image":
        extra = f" img={b.get('img_path','')[-30:]}"
    print(f"[{i:3d}] pg={b.get('page_idx','?'):2} type={b['type']:10} | {repr(t)}{extra}")
