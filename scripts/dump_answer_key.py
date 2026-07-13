"""Dump last 80 blocks of a MinerU output to find answer key format."""
import json, pathlib, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for folder_name in [
    "35e51914-678e-46e4-9bff-7c7de6b18e7f",
    "bf696604-3cba-4e15-a92b-7fb9a40d2484",
    "cd5f9180-b7da-4005-9d6a-8c626ba78545",
]:
    p = pathlib.Path(f"C:/Users/Anurag shukla/mocktest/storage/mineru_outputs/{folder_name}")
    cl = list(p.rglob("*content_list*"))
    if not cl:
        print(f"[{folder_name[:8]}] NO content_list found")
        continue
    data = json.loads(cl[0].read_text(encoding="utf-8"))
    print(f"\n{'='*70}")
    print(f"Folder: {folder_name[:8]}  Total blocks: {len(data)}")
    print(f"{'='*70}")
    # Show last 60 blocks
    for i, b in enumerate(data[-60:], start=len(data)-60):
        t = b.get("text", "")[:120].replace("\n", "↵")
        extra = f" img={b.get('img_path','')[-25:]}" if b.get("type") == "image" else ""
        print(f"[{i:3d}] pg={b.get('page_idx','?'):2} type={b['type']:10} | {repr(t)}{extra}")
