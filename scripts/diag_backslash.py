"""Diagnostic: determine exact backslash encoding in MinerU equation blocks."""
import json, pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = pathlib.Path(
    "C:/Users/Anurag shukla/mocktest/storage/mineru_outputs/"
    "56902aba-584d-4774-9502-6d9e8773d74a"
)
data = json.loads(list(p.rglob("*content_list*"))[0].read_text(encoding="utf-8"))
eq = data[51].get("text", "")

print("=== RAW BYTES ===")
print("len:", len(eq))
print("repr:", repr(eq))
print()

# Character-by-character for first 30 chars
print("=== FIRST 30 CHARS ===")
for i in range(min(30, len(eq))):
    print(f"  [{i:2d}] ord={ord(eq[i]):3d} char={repr(eq[i])}")
print()

# Guard check
one_bs_begin = "\\" + "begin"  # 1 backslash + begin
two_bs_begin = "\\\\" + "begin"  # 2 backslashes + begin
print("=== GUARD CHECKS ===")
print(f"one_bs_begin repr: {repr(one_bs_begin)}")
print(f"two_bs_begin repr: {repr(two_bs_begin)}")
print(f"one_bs in eq: {one_bs_begin in eq}")
print(f"two_bs in eq: {two_bs_begin in eq}")
print()

# After $$ strip
text = eq.replace("$$", " ")
print("=== AFTER $$ STRIP ===")
print("repr:", repr(text))
print()

# Regex strip begin/end array
text2 = re.sub(r"\\begin\s*\{\s*array\s*\}\s*(?:\{[^}]*\})?\s*", " ", text)
text2 = re.sub(r"\\end\s*\{\s*array\s*\}", " ", text2)
print("=== AFTER begin/end STRIP ===")
print("repr:", repr(text2))
print()

# Split on row separator  
cells = re.split(r"\\\\|&", text2)
print("=== CELLS ===")
for i, c in enumerate(cells):
    c = c.strip()
    if c:
        print(f"  Cell [{i}]: {repr(c)}")
print()

# Test _CELL_OPT_RE on each cell
sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")
from app.services.question_builder.full_paper import _CELL_OPT_RE

print("=== _CELL_OPT_RE PATTERN ===")
print("pattern:", repr(_CELL_OPT_RE.pattern))
print()

for i, c in enumerate(cells):
    c = c.strip()
    if c:
        m = _CELL_OPT_RE.search(c)
        if m:
            print(f"  Cell [{i}]: MATCH groups={m.groups()}")
        else:
            print(f"  Cell [{i}]: NO MATCH (first 60 chars: {repr(c[:60])})")
