"""Trace Q2 equation block step by step."""
import json, pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = pathlib.Path(
    "C:/Users/Anurag shukla/mocktest/storage/mineru_outputs/"
    "56902aba-584d-4774-9502-6d9e8773d74a"
)
data = json.loads(list(p.rglob("*content_list*"))[0].read_text(encoding="utf-8"))
eq = data[10].get("text", "")

print("=== Q2 EQUATION BLOCK ===")
print("repr:", repr(eq))
print("len:", len(eq))
print()

# Step 1: $$ strip
text = eq.replace("$$", " ")
print("After $$ strip:", repr(text))
print()

# Step 2: begin/end strip
text2 = re.sub(r"\\begin\s*\{\s*array\s*\}\s*(?:\{[^}]*\})?\s*", " ", text)
text2 = re.sub(r"\\end\s*\{\s*array\s*\}", " ", text2)
print("After begin/end strip:", repr(text2))
print()

# Step 3: Row split
cells = re.split(r"\\\\|&", text2)
print("Cells after split:")
for i, c in enumerate(cells):
    print(f"  [{i}] repr: {repr(c.strip())}")
print()

# Now check what _CELL_OPT_RE sees
sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")
from app.services.question_builder.full_paper import _CELL_OPT_RE

print("_CELL_OPT_RE pattern:", repr(_CELL_OPT_RE.pattern))
print()
for i, c in enumerate(cells):
    c = c.strip()
    if c:
        m = _CELL_OPT_RE.search(c)
        if m:
            print(f"Cell [{i}]: MATCH groups={m.groups()}")
        else:
            print(f"Cell [{i}]: NO MATCH")
            # Try to find \left in the cell
            if "\\left" in c:
                print(f"  Contains \\left! Content: {repr(c[:120])}")
