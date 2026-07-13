"""Patch line 118 of full_paper.py to fix _CELL_OPT_RE.

The issue: (?:\\\\right) comes AFTER \\) in the regex, but in actual MinerU content
\\right comes BEFORE the closing paren: \\left( 2 \\right)

Fix: move (?:\\\\right\\s*) to just before \\) so it matches the actual token order.
"""
import pathlib, sys, re

fp = pathlib.Path(
    "C:/Users/Anurag shukla/mocktest/app/services/question_builder/full_paper.py"
)
lines = fp.read_text(encoding="utf-8").splitlines(keepends=True)

# Line 118 (0-indexed: 117) contains the broken marker pattern
old_line = lines[117]
print("Old line 118:", repr(old_line))

# Build the correct replacement line
# The correct regex part should be:
#   (?:\\left\s*)?\(?\s*([1-4])\s*(?:\\right\s*)?\)\s*
# In the source file this is written as:
#   r"(?:\\\\left\\s*)?\\(?\\s*([1-4])\\s*(?:\\\\right\\s*)?\\)\\s*"
new_line = '    r"(?:\\\\\\\\left\\\\s*)?\\\\(?\\\\s*([1-4])\\\\s*(?:\\\\\\\\right\\\\s*)?\\\\)\\\\s*"  # (N), N), or \\\\left(N\\\\right)\n'
print("New line 118:", repr(new_line))

lines[117] = new_line
fp.write_text("".join(lines), encoding="utf-8")
print("Patched!")

# Verify
import importlib
sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")
if "app.services.question_builder.full_paper" in sys.modules:
    del sys.modules["app.services.question_builder.full_paper"]
if "app.services.question_builder.base" in sys.modules:
    del sys.modules["app.services.question_builder.base"]

from app.services.question_builder.full_paper import _CELL_OPT_RE

print("Pattern:", repr(_CELL_OPT_RE.pattern))

test1 = "{ { \\left( 2 \\right) 3 + e } }"
test2 = "{ { 1 ) 3 \\pi + 8 } }"
test3 = "{ { ( 2 ) e^2+1 } }"

for label, t in [("\\left(N\\right)", test1), ("N)", test2), ("(N)", test3)]:
    m = _CELL_OPT_RE.search(t)
    if m:
        print(f"  {label}: MATCH -> digit={m.group(1)}, content={repr(m.group(2).strip())}")
    else:
        print(f"  {label}: NO MATCH on {repr(t)}")
