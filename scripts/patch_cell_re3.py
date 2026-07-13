"""Patch _CELL_OPT_RE line 118 by constructing the exact target bytes."""
import pathlib

fp = pathlib.Path(
    "C:/Users/Anurag shukla/mocktest/app/services/question_builder/full_paper.py"
)
lines = fp.read_text(encoding="utf-8").splitlines(keepends=True)

BS = chr(92)  # single backslash character

# The regex pattern we want (as it appears inside the raw string in source code):
#   (?:\\left\s*)?\(?\s*([1-4])\s*(?:\\right\s*)?\)\s*
#
# In the .py source file, inside r"...", backslashes are literal.
# So the source text is exactly:
#   (?:\\left\s*)?\(?\s*([1-4])\s*(?:\\right\s*)?\)\s*

pattern_part = (
    "(?:"
    + BS + BS + "left"       # \\left (two chars in source = literal \left in regex)
    + BS + "s*)?"            # \s*)?
    + BS + "(?"              # \(?
    + BS + "s*([1-4])"       # \s*([1-4])
    + BS + "s*"              # \s*
    + "(?:"
    + BS + BS + "right"      # \\right
    + BS + "s*)?"            # \s*)?
    + BS + ")"               # \)
    + BS + "s*"              # \s*
)

comment = "  # (N), N), or " + BS + BS + "left(N" + BS + BS + "right)"

new_line = '    r"' + pattern_part + '"' + comment + "\n"

print("Old line 118:", repr(lines[117]))
print("New line 118:", repr(new_line))

lines[117] = new_line
fp.write_text("".join(lines), encoding="utf-8")
print("Patched line 118!")

# Verify it parses
import sys, re
sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")

# Clear all cached modules
for mod_name in list(sys.modules):
    if "question_builder" in mod_name:
        del sys.modules[mod_name]

from app.services.question_builder.full_paper import _CELL_OPT_RE

print("Compiled pattern:", repr(_CELL_OPT_RE.pattern))

# Test cases
test1 = "{ { " + BS + "left( 2 " + BS + "right) 3 + e } }"
test2 = "{ { 1 ) 3 " + BS + "pi + 8 } }"
test3 = "{ { ( 2 ) e^2+1 } }"

print()
for label, t in [("left-right", test1), ("bare-N)", test2), ("paren-(N)", test3)]:
    m = _CELL_OPT_RE.search(t)
    if m:
        print("  " + label + ": MATCH -> digit=" + m.group(1) + ", content=" + repr(m.group(2).strip()))
    else:
        print("  " + label + ": NO MATCH on " + repr(t))
