"""Check: how many pages total, and what's on the last pages (answer key pages)."""
import json, pathlib, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Check the most recent full-paper output
for folder_id in [
    "35e51914-678e-46e4-9bff-7c7de6b18e7f",
    "bf696604-3cba-4e15-a92b-7fb9a40d2484",
]:
    p = pathlib.Path(f"C:/Users/Anurag shukla/mocktest/storage/mineru_outputs/{folder_id}")
    cl = list(p.rglob("*content_list*"))
    if not cl:
        continue
    data = json.loads(cl[0].read_text(encoding="utf-8"))

    pages = sorted(set(b.get("page_idx", 0) for b in data))
    print(f"\nFolder: {folder_id[:8]}  Total blocks: {len(data)}  Pages: {pages}")

    # Show last 3 pages entirely
    last_pages = pages[-3:]
    for b in data:
        if b.get("page_idx") in last_pages:
            t = b.get("text", "")[:150].replace("\n", "↵")
            extra = f" img={b.get('img_path','')[-30:]}" if b["type"] == "image" else ""
            print(f"  pg={b['page_idx']:2} type={b['type']:10} | {repr(t)}{extra}")

    # Also check if there are other files in the folder (e.g. model output json)
    print(f"\n  Files in output folder:")
    for f in sorted(p.rglob("*")):
        if f.is_file() and f.suffix in (".json", ".md", ".txt"):
            print(f"    {f.name}  ({f.stat().st_size} bytes)")
