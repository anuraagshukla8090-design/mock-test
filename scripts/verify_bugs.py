"""
verify_bugs.py — Verify each suspected bug against real content_list data.

Runs the current builder and shows exactly what went wrong, with the raw
MinerU blocks side-by-side with the parsed result.
"""
import json, pathlib, sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Load content_list ─────────────────────────────────────────────────────────
p = pathlib.Path('C:/Users/Anurag shukla/mocktest/storage/mineru_outputs/56902aba-584d-4774-9502-6d9e8773d74a')
files = list(p.rglob('*content_list*'))
if not files:
    print("No content_list found"); sys.exit(1)
data = json.loads(files[0].read_text(encoding='utf-8'))

# ── Run current builder ───────────────────────────────────────────────────────
sys.path.insert(0, 'C:/Users/Anurag shukla/mocktest')
from app.services.question_builder.full_paper import FullPaperBuilder
from pathlib import Path

builder = FullPaperBuilder(data, Path('.'))
questions = builder.build()
q_map = {q.question_number: q for q in questions}

# ── Bug 1: Q13 — only 2 options ───────────────────────────────────────────────
print("=" * 65)
print("BUG 1: Q13 — option count and raw blocks")
print("=" * 65)
q13 = q_map.get(13)
if q13:
    print(f"  section_type : {q13.section_type}")
    print(f"  options      : {q13.options}")
    print(f"  answer       : {q13.answer!r}")
    print(f"  warnings     : {q13.warnings}")
else:
    print("  Q13 not found in output!")

print("\nRaw blocks 50-56 from content_list:")
for i in range(50, min(57, len(data))):
    b = data[i]
    print(f"  [{i}] type={b['type']!r:10} | {repr(b.get('text','')[:200])}")

print("\nVerify: does parse_latex_array_options work on the equation block?")
from app.services.question_builder.base import parse_latex_array_options, split_options_text
eq_text = data[51].get('text', '')
print(f"  Equation text: {repr(eq_text)}")
result = parse_latex_array_options(eq_text)
print(f"  parse_latex_array_options result: {result}")

# Also try split_options_text directly on extracted inner text
print("\nVerify: what does split_options_text see from block 51?")
# The equation block has "1) 3\pi + 8" — not "(1)" format
inner = re.sub(r'\$\$', '', eq_text)
inner = re.sub(r'\\begin\{array\}.*?(?=\d|\()', '', inner, flags=re.DOTALL)
inner = re.sub(r'\\end\{array\}', '', inner)
inner = inner.replace('\\\\', ' ').replace('&', ' ')
print(f"  After strip: {repr(inner[:200])}")
result2 = split_options_text(inner)
print(f"  split_options_text result: {result2}")

# What does the combined text for Q13 look like?
print("\nCombined text the builder sees for Q13:")
# Simulate what _build_question does
q13_blocks = [data[i] for i in range(50, 57)]
parts = [b.get('text','').strip() for b in q13_blocks if b['type'] in ('text','equation') and b.get('text','').strip()]
print(f"  Parts: {[repr(p[:80]) for p in parts]}")

# ── Bug 2: Q14 — (13)(24) format ─────────────────────────────────────────────
print()
print("=" * 65)
print("BUG 2: Q14 — (13)(24) option block format")
print("=" * 65)
q14 = q_map.get(14)
if q14:
    print(f"  section_type : {q14.section_type}")
    print(f"  options      : {q14.options}")
    print(f"  answer       : {q14.answer!r}")
    print(f"  stem snippet : {repr(q14.stem_md[:200])}")
    print(f"  warnings     : {q14.warnings}")
else:
    print("  Q14 not found in output!")

print("\nRaw blocks 57-60:")
for i in range(57, min(61, len(data))):
    b = data[i]
    print(f"  [{i}] type={b['type']!r:10} | {repr(b.get('text','')[:200])}")

# Check what OPTION_MARKER_RE finds in "(13)" and "(24)"
from app.services.question_builder.base import OPTION_MARKER_RE
block58_text = data[58].get('text', '')
block59_text = data[59].get('text', '')
print(f"\n  OPTION_MARKER_RE finds in block 58 {repr(block58_text[:100])}: {OPTION_MARKER_RE.findall(block58_text)}")
print(f"  OPTION_MARKER_RE finds in block 59 {repr(block59_text[:100])}: {OPTION_MARKER_RE.findall(block59_text)}")

# ── Bug 3: Q31 — missing options ──────────────────────────────────────────────
print()
print("=" * 65)
print("BUG 3: Q31 — options dropped by MinerU")
print("=" * 65)
q31 = q_map.get(31)
if q31:
    print(f"  section_type : {q31.section_type}")
    print(f"  options      : {q31.options}")
    print(f"  answer       : {q31.answer!r}")
    print(f"  warnings     : {q31.warnings}")
else:
    print("  Q31 not found in output!")

print("\nRaw blocks 112-115 (Q31 area):")
for i in range(112, min(116, len(data))):
    b = data[i]
    print(f"  [{i}] type={b['type']!r:10} | {repr(b.get('text','')[:200])}")

# ── Bug 4: Q38 — options after image gap + (13)(24) format ───────────────────
print()
print("=" * 65)
print("BUG 4: Q38 — long image gap + (13)(24) format")
print("=" * 65)
q38 = q_map.get(38)
if q38:
    print(f"  section_type : {q38.section_type}")
    print(f"  options      : {q38.options}")
    print(f"  answer       : {q38.answer!r}")
    print(f"  stem snippet : {repr(q38.stem_md[:300])}")
    print(f"  warnings     : {q38.warnings}")
else:
    print("  Q38 not found in output!")

print("\nRaw blocks 154-170 (Q38 area):")
for i in range(154, min(171, len(data))):
    b = data[i]
    print(f"  [{i}] type={b['type']!r:10} | {repr(b.get('text','')[:150])}")

# ── Q30 — scattered option blocks ────────────────────────────────────────────
print()
print("=" * 65)
print("BONUS: Q30 — scattered/interleaved option blocks")
print("=" * 65)
q30 = q_map.get(30)
if q30:
    print(f"  section_type : {q30.section_type}")
    print(f"  options      : {q30.options}")
    print(f"  answer       : {q30.answer!r}")
    print(f"  warnings     : {q30.warnings}")

print("\nRaw blocks 106-112 (Q30 area):")
for i in range(106, min(113, len(data))):
    b = data[i]
    print(f"  [{i}] type={b['type']!r:10} | {repr(b.get('text','')[:150])}")

# ── Q12 — check equation block after Q12 ──────────────────────────────────────
print()
print("=" * 65)
print("BONUS: Q12 — equation block for options (2)(4)")
print("=" * 65)
q12 = q_map.get(12)
if q12:
    print(f"  section_type : {q12.section_type}")
    print(f"  options      : {q12.options}")
    print(f"  answer       : {q12.answer!r}")
    print(f"  warnings     : {q12.warnings}")

eq_text_49 = data[49].get('text', '')
print(f"\n  Block 49 (equation): {repr(eq_text_49)}")
result_49 = parse_latex_array_options(eq_text_49)
print(f"  parse_latex_array_options: {result_49}")

# ── Summary: all questions, section_type ──────────────────────────────────────
print()
print("=" * 65)
print("ALL PARSED QUESTIONS — type and option count")
print("=" * 65)
for q in sorted(questions, key=lambda x: x.question_number):
    n_opts = len(q.options)
    flag = ''
    if q.section_type == 'integer' and q.answer in ('A','B','C','D'):
        flag = ' <-- WRONG: integer but answer is letter'
    if q.section_type == 'mcq' and n_opts < 4:
        flag = f' <-- WRONG: MCQ but only {n_opts} options'
    ans_hint = q.answer or 'MISSING'
    print(f"  Q{q.question_number:>3}  {q.section_type:<8}  opts={n_opts}  ans={ans_hint:<6}{flag}")
