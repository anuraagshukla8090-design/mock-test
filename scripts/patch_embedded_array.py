"""
Patch: add _parse_text_embedded_array() to full_paper.py and wire it into _build_question.

The Q11 pattern: a text block starting with "( $\begin{array}..." where MinerU
merged an option array into a text block. The block contains options (2) and (4)
inside a \begin{array}...\end{array} wrapped in $...$.

This is different from equation blocks (type='equation') — the block type is 'text'.

Strategy:
1. Detect: text block matching r"^\(\s*\$\\begin\{array\}"
2. Extract the $..$ portion → parse it like an equation block
3. Return the options dict or {} if unparseable
"""
import pathlib, re

fp = pathlib.Path(
    "C:/Users/Anurag shukla/mocktest/app/services/question_builder/full_paper.py"
)
content = fp.read_text(encoding="utf-8")

# We'll insert the new helper _parse_text_embedded_array right after the
# _parse_equation_block_options function. Find the end of that function:
INSERT_AFTER = "    return options if len(options) >= 2 else {}\n"

NEW_FUNCTION = '''

def _parse_text_embedded_array(text: str) -> dict[str, str]:
    """
    Handle a MinerU text block that contains an embedded LaTeX array.

    MinerU sometimes outputs option arrays inside type='text' blocks rather
    than type='equation' blocks, producing content like:
      "( $\\\\begin{array} { c } { { 2 ) 22\\\\pi^2 } } \\\\\\\\ { { 4 ) 18\\\\pi^2 } } \\\\end{array}$ "

    This block starts with a bare "(" that is NOT an option marker (the (2)(4)
    markers are INSIDE the array). We detect it by the leading "( $\\\\begin{array}"
    pattern and extract the embedded $...$ expression as an equation block.

    Returns {} if:
    - The text does not start with a bare "(" followed by an array expression
    - The embedded array cannot be parsed (falls through to _parse_equation_block_options)
    """
    # Detect: text block starting with ( followed immediately by a $\\begin{array}
    # The space and $ come right after the opening (
    if not re.match(r"^\\(\\s*\\$\\s*\\\\begin", text.strip()):
        return {}

    # Extract the $...$ expression from the text block
    # Find the first $ and the matching closing $
    start = text.find("$")
    end = text.rfind("$")
    if start == -1 or end <= start:
        return {}

    embedded = "$$" + text[start + 1:end] + "$$"
    return _parse_equation_block_options(embedded)

'''

# Find insertion point (after the closing line of _parse_equation_block_options)
idx = content.find(INSERT_AFTER)
if idx == -1:
    print("ERROR: insertion point not found")
    print("Searching for nearby text...")
    for i, line in enumerate(content.splitlines()):
        if "len(options) >= 2" in line:
            print(f"  Line {i+1}: {repr(line)}")
else:
    insert_pos = idx + len(INSERT_AFTER)
    content = content[:insert_pos] + NEW_FUNCTION + content[insert_pos:]
    fp.write_text(content, encoding="utf-8")
    print("Inserted _parse_text_embedded_array after _parse_equation_block_options")

# Now wire it into _build_question: inside the text block processing,
# before checking for merged markers, check for embedded array
# The existing code in _build_question for text blocks is:
#
#   t = normalize_text_block(block.get("text", ""))
#   if not t:
#       continue
#   # Check for MinerU merged option marker blocks: "(13) $a$ $b$"
#   merged = _split_merged_option_block(t)
#   if merged is None:
#       # Normal text block
#       text_parts.append(t)
#   else:
#       extra_options.update(merged)
#
# We need to add: check for embedded array BEFORE the merged check
# because "(  $\begin{array}..." starts with "(" which would confuse _split_merged_option_block

content = fp.read_text(encoding="utf-8")

OLD_TEXT_HANDLING = '''            # Check for MinerU merged option marker blocks: "(13) $a$ $b$"
            merged = _split_merged_option_block(t)
            if merged is None:
                # Normal text block — add to the combined text for stem/option parsing
                text_parts.append(t)
            else:
                # Was a merged-marker block: consume it for options (may be empty
                # if content couldn't be split — warning already logged inside)
                extra_options.update(merged)'''

NEW_TEXT_HANDLING = '''            # Check for text blocks with an embedded LaTeX array (e.g. Q11 pattern):
            # "( $\\begin{array}...\\end{array}$ " — MinerU merged an option array
            # into a text block. Parse it as an equation block.
            embedded = _parse_text_embedded_array(t)
            if embedded:
                extra_options.update(embedded)
                continue

            # Check for MinerU merged option marker blocks: "(13) $a$ $b$"
            merged = _split_merged_option_block(t)
            if merged is None:
                # Normal text block — add to the combined text for stem/option parsing
                text_parts.append(t)
            else:
                # Was a merged-marker block: consume it for options (may be empty
                # if content couldn't be split — warning already logged inside)
                extra_options.update(merged)'''

if OLD_TEXT_HANDLING in content:
    content = content.replace(OLD_TEXT_HANDLING, NEW_TEXT_HANDLING)
    fp.write_text(content, encoding="utf-8")
    print("Wired _parse_text_embedded_array into _build_question")
else:
    print("ERROR: _build_question text handling block not found")
    # Show context
    for i, line in enumerate(content.splitlines()):
        if "merged option marker" in line:
            print(f"  Line {i+1}: {repr(line)}")

# Verify
import sys, json
sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")
for mod_name in list(sys.modules):
    if "question_builder" in mod_name:
        del sys.modules[mod_name]

from app.services.question_builder.full_paper import (
    _parse_text_embedded_array,
    _parse_equation_block_options,
    FullPaperBuilder,
)
from pathlib import Path

# Test on the Q11 block 45
test_block = r"( $\begin{array} { c } { { 2 ) 2 2 \pi ^ { 2 } } } \\ { { 4 ) 1 8 \pi ^ { 2 } } } \end{array}$ "
result = _parse_text_embedded_array(test_block)
print(f"\n_parse_text_embedded_array on Q11 block: {result}")

p = pathlib.Path(
    "C:/Users/Anurag shukla/mocktest/storage/mineru_outputs/"
    "56902aba-584d-4774-9502-6d9e8773d74a"
)
data = json.loads(list(p.rglob("*content_list*"))[0].read_text(encoding="utf-8"))
builder = FullPaperBuilder(data, Path("."))
questions = builder.build()
q_map = {q.question_number: q for q in questions}

q11 = q_map.get(11)
if q11:
    print(f"Q11 after fix: section_type={q11.section_type}, opts={len(q11.options)}, options={q11.options}")
else:
    print("Q11 not found")

bad = [q for q in questions if q.section_type == "mcq" and len(q.options) < 4]
print(f"\nRemaining opts<4: {[q.question_number for q in bad]}")
