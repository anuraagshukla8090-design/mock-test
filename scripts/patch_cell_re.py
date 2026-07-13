"""Patch _CELL_OPT_RE to fix \\left(N\\right) matching.

The problem: the regex had (?:\\\\right) AFTER \\) but \\right comes BEFORE the )
in the actual content: \\left( 2 \\right)

Fix: move (?:\\\\right\\s*) before \\) in the pattern.
"""
import pathlib

fp = pathlib.Path(
    "C:/Users/Anurag shukla/mocktest/app/services/question_builder/full_paper.py"
)
content = fp.read_text(encoding="utf-8")

old_pattern = (
    r'    r"(?:\\\\left\\s*)?\\(?\\s*([1-4])\\s*\\)(?:\\\\right)?\\s*"'
    r'  # (N), N), or \\left(N\\right)'
)
new_pattern = (
    r'    r"(?:\\\\left\\s*)?\\(?\\s*([1-4])\\s*(?:\\\\right\\s*)?\\)\\s*"'
    r'  # (N), N), or \\left(N\\right)'
)

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    fp.write_text(content, encoding="utf-8")
    print("Patched _CELL_OPT_RE successfully!")
else:
    print("ERROR: old pattern not found in file")
    # Try to find it
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "CELL_OPT_RE" in line or "left" in line and "right" in line:
            print(f"  Line {i+1}: {repr(line)}")

# Verify
import importlib, sys, re, json
sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")

# Reimport
if "app.services.question_builder.full_paper" in sys.modules:
    del sys.modules["app.services.question_builder.full_paper"]
from app.services.question_builder.full_paper import _CELL_OPT_RE

print("New pattern:", repr(_CELL_OPT_RE.pattern))

# Test against actual content
test1 = "{ { \\left( 2 \\right) 3 + e } }"
test2 = "{ { 1 ) 3 \\pi + 8 } }"
test3 = "{ { ( 2 ) e^2+1 } }"

for label, t in [("\\left(N\\right)", test1), ("N)", test2), ("(N)", test3)]:
    m = _CELL_OPT_RE.search(t)
    if m:
        print(f"  {label}: MATCH -> digit={m.group(1)}, content={repr(m.group(2).strip())}")
    else:
        print(f"  {label}: NO MATCH on {repr(t)}")
