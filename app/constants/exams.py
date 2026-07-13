"""
Canonical exam and subject names.

All entry points that receive exam_name or subject from external sources
(upload form, LLM output, API requests) should call normalize_exam_name()
and normalize_subject() before storing to the database.

This prevents variants like "jee main", "JEE MAINS", "Jee Main" from
creating separate buckets in the question bank.
"""
from __future__ import annotations

# ── Canonical names ───────────────────────────────────────────────────────────

CANONICAL_EXAMS: list[str] = [
    "JEE Main",
    "JEE Advanced",
    "NEET",
    "CUET",
]

CANONICAL_SUBJECTS: list[str] = [
    "physics",
    "chemistry",
    "mathematics",
    "biology",
    "english",
    "hindi",
]

# Aliases → canonical mapping for exam names (case-insensitive keys)
_EXAM_ALIASES: dict[str, str] = {
    # JEE Main variations
    "jee main":        "JEE Main",
    "jee mains":       "JEE Main",
    "jee-main":        "JEE Main",
    "jee-mains":       "JEE Main",
    "jeemain":         "JEE Main",
    "jeemains":        "JEE Main",
    "jee":             "JEE Main",    # ambiguous, default to JEE Main
    "jee 2024":        "JEE Main",
    "jee main 2024":   "JEE Main",
    "iit jee":         "JEE Main",

    # JEE Advanced variations
    "jee advanced":    "JEE Advanced",
    "jee adv":         "JEE Advanced",
    "jee-advanced":    "JEE Advanced",
    "iit jee advanced":"JEE Advanced",
    "advanced":        "JEE Advanced",

    # NEET variations
    "neet":            "NEET",
    "neet ug":         "NEET",
    "neet-ug":         "NEET",
    "neet 2024":       "NEET",

    # CUET variations
    "cuet":            "CUET",
    "cuet ug":         "CUET",
    "cuet 2024":       "CUET",
}

# Aliases → canonical mapping for subject names (case-insensitive keys)
_SUBJECT_ALIASES: dict[str, str] = {
    "physics":      "physics",
    "phy":          "physics",
    "ph":           "physics",

    "chemistry":    "chemistry",
    "chem":         "chemistry",
    "ch":           "chemistry",

    "mathematics":  "mathematics",
    "maths":        "mathematics",
    "math":         "mathematics",
    "maths.":       "mathematics",

    "biology":      "biology",
    "bio":          "biology",

    "english":      "english",
    "eng":          "english",

    "hindi":        "hindi",
}


def normalize_exam_name(raw: str | None) -> str | None:
    """
    Normalize an exam name to its canonical form.

    Returns the canonical string (e.g. "JEE Main") or the original
    (stripped) value if no match is found.
    Returns None if input is None or blank/whitespace-only.
    """
    if not raw or not raw.strip():
        return None
    lookup = raw.strip().lower()
    # Direct alias lookup
    if lookup in _EXAM_ALIASES:
        return _EXAM_ALIASES[lookup]
    # Strip trailing years/session labels and try again
    # e.g. "JEE Main 2024 April" → "jee main"
    parts = lookup.split()
    for length in range(len(parts), 0, -1):
        candidate = " ".join(parts[:length])
        if candidate in _EXAM_ALIASES:
            return _EXAM_ALIASES[candidate]
    # No match → return original as-is (do not corrupt user data)
    return raw.strip()


def normalize_subject(raw: str | None) -> str | None:
    """
    Normalize a subject name to its canonical lowercase form.

    Returns the canonical string (e.g. "physics") or the original
    (lowercased) value if no match is found.
    Returns None if input is None or blank.
    """
    if not raw:
        return None
    lookup = raw.strip().lower()
    return _SUBJECT_ALIASES.get(lookup, lookup)
