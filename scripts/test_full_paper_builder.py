"""
test_full_paper_builder.py

Offline unit test for FullPaperBuilder — no PDF, no LLM, no DB needed.
Simulates a realistic JEE Main content_list with:
  - Page headers (noise)
  - MathonGo watermarks (noise)
  - 5 Math MCQ questions (Q1–Q5, options inline)
  - 2 Math Integer questions (Q21–Q22, no options)
  - 2 Physics MCQ questions (Q26–Q27, options on next block)
  - Answer key section at end

Run:
    .venv\\Scripts\\python scripts\\test_full_paper_builder.py
"""
import sys
import os

# Add project root so imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from app.services.question_builder.full_paper import FullPaperBuilder

FAKE_IMAGES_DIR = Path(".")  # no real images in this test


def make_blocks():
    return [
        # ── Page headers (noise) ────────────────────────────────────────────
        {"type": "text", "text": "2025 (22 Jan Shift 1)", "text_level": 1, "page_idx": 0},
        {"type": "text", "text": "JEE Main Previous Year Paper", "text_level": 1, "page_idx": 0},
        {"type": "text", "text": "JEE Main 2025 January", "page_idx": 0},
        {"type": "text", "text": "MathonGo", "text_level": 1, "page_idx": 0},

        # ── Watermarks ──────────────────────────────────────────────────────
        {"type": "text", "text": "mathongo mathongo mathongo", "page_idx": 0},

        # ── Q1 (Math MCQ) ───────────────────────────────────────────────────
        {
            "type": "text",
            "text": "Q1. Let $a_1, a_2, a_3, \\ldots$ be a G.P. of increasing positive terms. "
                    "If $a_1 a_5 = 28$ and $a_2 + a_4 = 29$, then $a_6$ is equal to:",
            "page_idx": 0,
        },
        {
            "type": "text",
            "text": "(1) 628   (2) 812   (3) 784   (4) 526",
            "page_idx": 0,
        },

        # ── Q2 (Math MCQ, options on separate block) ────────────────────────
        {
            "type": "text",
            "text": "Q2. Let $x = x(y)$ be the solution of the differential equation. If $x(1) = 1$, then $x(1/e)$ is:",
            "page_idx": 0,
        },
        {"type": "text", "text": "(1) $\\frac{1}{2} + e$", "page_idx": 0},
        {"type": "text", "text": "(2) $3 + e$", "page_idx": 0},
        {"type": "text", "text": "(3) $3 - e$", "page_idx": 0},
        {"type": "text", "text": "(4) $\\frac{3}{2} + e$", "page_idx": 0},

        # ── Q3 (Math MCQ) ───────────────────────────────────────────────────
        {
            "type": "text",
            "text": "Q3. Two balls are selected at random. If the probability is $\\frac{m}{n}$, $\\gcd(m,n)=1$, then $m-n$ is:",
            "page_idx": 1,
        },
        {"type": "text", "text": "(1) 4   (2) 14   (3) 13   (4) 11", "page_idx": 1},

        # ── Q4 (Math MCQ) ───────────────────────────────────────────────────
        {
            "type": "text",
            "text": "Q4. The product of all solutions of $e^{5(\\log_e x)^2 + 3} = x^8$, $x > 0$, is:",
            "page_idx": 1,
        },
        {"type": "text", "text": "(1) $e^{9/5}$   (2) $e^{6/5}$   (3) $e^8$   (4) $e$", "page_idx": 1},

        # ── Q5 (Math MCQ) ───────────────────────────────────────────────────
        {
            "type": "text",
            "text": "Q5. Let the triangle PQR be the image of the triangle. Then $15(\\alpha - \\beta)$ is equal to:",
            "page_idx": 1,
        },
        {"type": "text", "text": "(1) 19   (2) 24   (3) 21   (4) 22", "page_idx": 1},

        # ── Page 2 noise ─────────────────────────────────────────────────────
        {"type": "text", "text": "2025 (22 Jan Shift 1)", "text_level": 1, "page_idx": 2},
        {"type": "text", "text": "JEE Main Previous Year Paper", "text_level": 1, "page_idx": 2},
        {"type": "text", "text": "3", "page_idx": 2},  # page number

        # ── Q21 (Math Integer, no options) ──────────────────────────────────
        {
            "type": "text",
            "text": "Q21. Let $A$ be a square matrix of order 3 such that $\\det(A) = -2$ and "
                    "$\\det(3 \\text{adj}(-6 \\text{adj}(3A))) = 2^{m+n} \\cdot 3^m$, $m > n$. "
                    "Then $4m + 2n$ is equal to ______.",
            "page_idx": 2,
        },
        # No options block for integer questions

        # ── Q22 (Math Integer) ──────────────────────────────────────────────
        {
            "type": "text",
            "text": "Q22. If $\\sum_{r=0}^{5} \\frac{11 C_{2r}}{6} = \\frac{m}{n}$, $\\gcd(m,n)=1$, "
                    "then $m - n$ is equal to ______.",
            "page_idx": 2,
        },

        # ── Q26 (Physics MCQ) ───────────────────────────────────────────────
        {
            "type": "text",
            "text": "Q26. An electron is made to enter symmetrically between two parallel plates. "
                    "The electron emerges with a horizontal component of velocity $10^6$ m/s. "
                    "The vertical component is:",
            "page_idx": 3,
        },
        {"type": "text", "text": "(1) 0   (2) $1 \\times 10^6$ m/s   (3) $16 \\times 10^6$ m/s   (4) $16 \\times 10^4$ m/s", "page_idx": 3},

        # ── Q27 (Physics MCQ, assertion-reason) ─────────────────────────────
        {
            "type": "text",
            "text": "Q27. Given below are two statements: Statement-I: The equivalent emf of two non-ideal batteries connected in parallel is smaller than either of the two emfs. "
                    "Statement-II: The internal resistance is smaller than either of the two batteries.",
            "page_idx": 3,
        },
        {
            "type": "text",
            "text": "(1) Both Statement-I and Statement-II are false   "
                    "(2) Statement-I is false but Statement-II is true   "
                    "(3) Both Statement-I and Statement-II are true   "
                    "(4) Statement-I is true but Statement-II is false",
            "page_idx": 3,
        },

        # ── Answer key section ───────────────────────────────────────────────
        {"type": "text", "text": "ANSWER KEYS", "text_level": 1, "page_idx": 13},
        {
            "type": "text",
            "text": "1.(4) 2.(3) 3.(2) 4.(1) 5.(4) 6.(2) 7.(3) 8.(1) 9.(1) 10.(1)",
            "page_idx": 13,
        },
        {
            "type": "text",
            "text": "21.(34) 22.(2035) 23.(16) 24.(34) 25.(216) 26.(3) 27.(4)",
            "page_idx": 13,
        },
    ]


def run():
    blocks = make_blocks()
    builder = FullPaperBuilder(blocks, FAKE_IMAGES_DIR)
    questions = builder.build()

    print(f"\n{'='*60}")
    print(f"FullPaperBuilder Test Results")
    print(f"{'='*60}")
    print(f"Total questions: {len(questions)}")
    print()

    errors = []
    for q in questions:
        opts = f"  opts={list(q.options.keys())}" if q.options else "  [integer]"
        print(
            f"  Q{q.question_number:>3}  {q.section_type:<8}{opts:<20}"
            f"  ans={q.answer!r:<8}  page={q.source_page}"
        )
        if q.warnings:
            for w in q.warnings:
                print(f"         WARNING: {w}")
        # Assertions
        if q.question_number in (1, 2, 3, 4, 5, 26, 27) and q.section_type != "mcq":
            errors.append(f"Q{q.question_number} should be MCQ but got {q.section_type!r}")
        if q.question_number in (21, 22) and q.section_type != "integer":
            errors.append(f"Q{q.question_number} should be integer but got {q.section_type!r}")
        if q.question_number == 1 and q.answer != "D":
            errors.append(f"Q1 answer should be D (1→A,2→B,3→C,4→D from 4→D) but got {q.answer!r}")
        if q.question_number == 21 and q.answer != "34":
            errors.append(f"Q21 integer answer should be '34' but got {q.answer!r}")
        if q.question_number == 22 and q.answer != "2035":
            errors.append(f"Q22 integer answer should be '2035' but got {q.answer!r}")
        if q.subject is not None:
            errors.append(f"Q{q.question_number}: subject should be None (set by LLM later) but got {q.subject!r}")

    print()
    print("Builder report:")
    for k, v in builder.report.items():
        print(f"  {k}: {v}")

    print()
    if errors:
        print(f"FAILED — {len(errors)} assertion(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print("ALL ASSERTIONS PASSED [OK]")
        sys.exit(0)


if __name__ == "__main__":
    run()
