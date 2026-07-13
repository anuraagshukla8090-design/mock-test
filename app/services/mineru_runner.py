from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import settings


@dataclass
class MineruOutput:
    """Result of running MinerU on a single PDF."""
    content_list: list[dict]      # Parsed content_list.json
    images_dir: Path              # Path to images/ subdirectory
    markdown: str                 # Raw markdown string
    source_pdf: str               # Original filename
    output_dir: Path              # Root output directory (stored in ingestions.mineru_output_dir)
    page_count: int               # Approximate page count


class MineruError(Exception):
    """Raised when MinerU processing fails."""
    pass


def run_mineru(pdf_path: Path, output_dir: Path) -> MineruOutput:
    """
    Run MinerU extraction on a single PDF.

    Calls the run_mineru_single.py script via subprocess using the MinerU
    Python environment (.venv310). This keeps the heavy ML dependencies
    (magic-pdf, torch) separate from the FastAPI application environment.

    Args:
        pdf_path:   Absolute path to the PDF file.
        output_dir: Directory where MinerU writes its output.
                    Created if it does not exist.

    Returns:
        MineruOutput with all parsed content.

    Raises:
        MineruError: If the subprocess fails or output files are missing.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if not settings.mineru_python:
        raise MineruError(
            "MINERU_PYTHON is not configured. "
            "Set it in your .env file to the absolute path of the Python interpreter "
            "that has magic-pdf installed (e.g. /path/to/.venv310/bin/python)."
        )

    cmd = [
        settings.mineru_python,
        settings.mineru_script,
        "--pdf", str(pdf_path),
        "--output-dir", str(output_dir),
    ]

    start = time.time()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,  # 10 minutes max
    )
    elapsed = time.time() - start

    if result.returncode != 0:
        raise MineruError(
            f"MinerU failed (exit {result.returncode}):\n"
            f"STDOUT: {result.stdout[-2000:]}\n"
            f"STDERR: {result.stderr[-2000:]}"
        )

    # Locate output files
    # MinerU creates: <output_dir>/<pdf_stem>/<pdf_stem>_content_list.json
    #                  <output_dir>/<pdf_stem>/<pdf_stem>.md
    #                  <output_dir>/<pdf_stem>/images/
    pdf_stem = pdf_path.stem
    result_dir = output_dir / pdf_stem

    content_list_path = result_dir / f"{pdf_stem}_content_list.json"
    markdown_path = result_dir / f"{pdf_stem}.md"
    images_dir = result_dir / "images"

    if not content_list_path.exists():
        raise MineruError(
            f"MinerU succeeded but content_list.json not found at {content_list_path}. "
            f"stdout: {result.stdout[-1000:]}"
        )

    with open(content_list_path, encoding="utf-8") as f:
        content_list = json.load(f)

    markdown = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""

    # Count approximate pages from content blocks
    page_indices = {b.get("page_idx", 0) for b in content_list if isinstance(b, dict)}
    page_count = max(page_indices, default=0) + 1

    # Ensure images dir exists even if MinerU found no images
    images_dir.mkdir(exist_ok=True)

    return MineruOutput(
        content_list=content_list,
        images_dir=images_dir,
        markdown=markdown,
        source_pdf=pdf_path.name,
        output_dir=result_dir,
        page_count=page_count,
    )


def run_ocr_on_image(img_path: Path) -> str:
    """
    Run MinerU's bundled PaddleOCR on a single image file via subprocess.

    Called by FullPaperBuilder when LayoutLMv3 emits the answer key page as a
    plain image (type=table/image with only img_path, no text/html).

    Uses the .venv310 Python interpreter configured in settings.mineru_python —
    the same environment that has magic_pdf and its OCR weights installed.

    Args:
        img_path: Absolute path to the image file.

    Returns:
        Raw OCR text string (joined fragments), or "" on failure.

    Raises:
        Never raises — always returns empty string on error so the calling
        builder can fall back to answer=None gracefully.
    """
    ocr_script = Path(settings.mineru_script).parent / "ocr_answer_key.py"
    if not ocr_script.exists():
        import logging
        logging.getLogger(__name__).warning(
            "ocr_answer_key.py not found at %s — skipping OCR fallback", ocr_script
        )
        return ""

    try:
        cmd = [
            settings.mineru_python,
            str(ocr_script),
            "--image", str(img_path),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            import logging
            logging.getLogger(__name__).warning(
                "OCR fallback failed (exit %d): %s", result.returncode, result.stderr[-500:]
            )
            return ""

        import json as _json
        data = _json.loads(result.stdout.strip())
        return data.get("text", "")

    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("OCR fallback error: %s", exc)
        return ""

