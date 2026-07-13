"""Full pipeline trace to find why answer key is not parsed."""
import sys, json, pathlib, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")

from app.services.post_processor import clean_content_blocks
from app.services.question_builder.full_paper import _find_answer_key_boundary, _parse_answer_key

for folder_id in [
    "35e51914-678e-46e4-9bff-7c7de6b18e7f",
    "bf696604-3cba-4e15-a92b-7fb9a40d2484",
]:
    p = pathlib.Path(f"C:/Users/Anurag shukla/mocktest/storage/mineru_outputs/{folder_id}")
    raw = json.loads(list(p.rglob("*content_list*"))[0].read_text(encoding="utf-8"))
    clean = clean_content_blocks(raw)
    
    print(f"\n{'='*60}")
    print(f"Folder: {folder_id[:8]}  raw={len(raw)} -> clean={len(clean)}")

    # Check for any answer-key-like text in clean blocks
    ANS_RE = re.compile(r"\b\d{1,3}\s*\.\s*\(\s*[^)]{1,8}\s*\)")
    found_any = False
    for i, b in enumerate(clean):
        if b.get("type") == "text":
            text = b.get("text", "")
            matches = ANS_RE.findall(text)
            if len(matches) >= 2:
                found_any = True
                print(f"  ans-block[{i}] pg={b.get('page_idx')}: {len(matches)} entries | {repr(text[:100])}")
    if not found_any:
        print("  NO answer-key text blocks found -> answer key is in images (MinerU data loss)")

    # Boundary + parse
    boundary = _find_answer_key_boundary(clean)
    ans_map = _parse_answer_key(clean[boundary:])
    print(f"  boundary={boundary}  answer_map_size={len(ans_map)}")

    # Show what's on the last 3 pages
    all_pages = sorted(set(b.get("page_idx", 0) for b in clean))
    last_pages = set(all_pages[-3:])
    print(f"  Last 3 pages: {sorted(last_pages)}")
    for b in clean:
        if b.get("page_idx") in last_pages:
            t = b.get("text", "")[:80].replace("\n", "↵")
            extra = f" img={b.get('img_path','')[-20:]}" if b["type"] == "image" else ""
            print(f"    pg={b['page_idx']} type={b['type']:10} | {repr(t)}{extra}")
