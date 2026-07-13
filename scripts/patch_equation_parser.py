"""Patch the _parse_equation_block_options function body in full_paper.py.

This script replaces lines 692-725 with the corrected version.
The two bugs being fixed:
1. Guard check uses wrong backslash count (4 instead of 2 in source = 1 actual)
2. Missing `text = eq_text` assignment before `text.replace(...)`
3. regex patterns use extra backslashes
"""
import pathlib

fp = pathlib.Path(
    "C:/Users/Anurag shukla/mocktest/app/services/question_builder/full_paper.py"
)
lines = fp.read_text(encoding="utf-8").splitlines(keepends=True)

# The correct function body for lines 692-725 (0-indexed: 691-724)
# Key facts from byte-level analysis:
#   - MinerU content has 1 backslash before LaTeX commands: \begin, \end, \left, \pi
#   - Row separator is 2 backslashes: \\
#   - In Python source: "\\begin" = 1 backslash + begin
#   - In Python source: r"\\begin" as regex = matches 1 literal backslash + begin
#   - In Python source: r"\\\\" as regex = matches 2 literal backslashes

new_lines = [
    '    # Guard: must contain a LaTeX array.\n',
    '    # MinerU content has 1 actual backslash before commands: \\begin, \\end.\n',
    '    # In Python source, "\\\\begin" (non-raw) = 1 backslash char + "begin".\n',
    '    if "\\\\begin" not in eq_text:\n',
    '        return {}\n',
    '\n',
    '    text = eq_text\n',
    '    # Strip $$ delimiters\n',
    '    text = text.replace("$$", " ")\n',
    '    # Strip \\begin{array}{format} — handles MinerU\'s spaced braces.\n',
    '    # r"\\\\begin" as regex pattern matches 1 literal backslash + "begin".\n',
    '    text = re.sub(r"\\\\begin\\s*\\{\\s*array\\s*\\}\\s*(?:\\{[^}]*\\})?\\s*", " ", text)\n',
    '    text = re.sub(r"\\\\end\\s*\\{\\s*array\\s*\\}", " ", text)\n',
    '    # Split on row separator (2 actual backslash chars in content).\n',
    '    # r"\\\\\\\\" as regex matches 2 literal backslashes. Also split on &.\n',
    '    cells = re.split(r"\\\\\\\\|&", text)\n',
    '\n',
    '    options: dict[str, str] = {}\n',
    '    for cell in cells:\n',
    '        cell = cell.strip()\n',
    '        if not cell:\n',
    '            continue\n',
    '        m = _CELL_OPT_RE.search(cell)\n',
    '        if m:\n',
    '            num_str = m.group(1)   # "1", "2", "3", or "4"\n',
    '            content = m.group(2).strip()\n',
    '            letter = NUM_TO_LETTER.get(num_str, num_str)\n',
    '            if content:\n',
    '                options[letter] = content\n',
    '\n',
    '    # Require at least 2 options for the result to be meaningful.\n',
    '    # A single match is more likely a false positive than a real option block.\n',
    '    return options if len(options) >= 2 else {}\n',
]

# Replace lines 692-725 (0-indexed 691-724)
lines[691:725] = new_lines

fp.write_text("".join(lines), encoding="utf-8")
print("Patched successfully!")
print(f"Replaced lines 692-725 with {len(new_lines)} new lines")

# Verify the patch by importing and testing
import json, sys
sys.path.insert(0, "C:/Users/Anurag shukla/mocktest")

# Force reimport
import importlib
import app.services.question_builder.full_paper as fp_mod
importlib.reload(fp_mod)

p = pathlib.Path(
    "C:/Users/Anurag shukla/mocktest/storage/mineru_outputs/"
    "56902aba-584d-4774-9502-6d9e8773d74a"
)
data = json.loads(list(p.rglob("*content_list*"))[0].read_text(encoding="utf-8"))

# Test block 51 (Q13 equation block with 1)/3) format)
b51 = data[51].get("text", "")
result_51 = fp_mod._parse_equation_block_options(b51)
print(f"\nQ13 equation block: {result_51}")

# Test block 10 (Q2 equation block with \left(2\right) format)
b10 = data[10].get("text", "")
result_10 = fp_mod._parse_equation_block_options(b10)
print(f"Q2 equation block: {result_10}")

# Test block 49 (Q12 equation block with (2)/(4) format)
b49 = data[49].get("text", "")
result_49 = fp_mod._parse_equation_block_options(b49)
print(f"Q12 equation block: {result_49}")

# Test block 93 (Q26 equation block with \left(N\right) format)
b93 = data[93].get("text", "")
result_93 = fp_mod._parse_equation_block_options(b93)
print(f"Q26 equation block: {result_93}")
