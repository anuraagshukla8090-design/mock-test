"""
run_mineru_single.py

Subprocess target called by app/services/mineru_runner.py.
Runs in the MinerU Python environment (.venv310) which has magic-pdf installed.
Processes a single PDF and writes output to the specified directory.

Usage:
    .venv310/Scripts/python.exe scripts/run_mineru_single.py \
        --pdf path/to/file.pdf \
        --output-dir path/to/output/

API compatibility: magic-pdf >= 1.3 (InferenceResult / PipeResult API)
  - pipe_txt_mode(imageWriter)  — positional, no image_writer kwarg
  - pipe_ocr_mode(imageWriter)  — positional, no image_writer kwarg
  - get_content_list(image_dir_prefix: str) -> str  (JSON string, not list)
  - dump_md(writer, filename, img_dir_prefix)  — 3 args required
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MinerU on a single PDF.")
    parser.add_argument("--pdf", required=True, help="Path to the PDF file.")
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    output_dir = Path(args.output_dir)

    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
        from magic_pdf.data.dataset import PymuDocDataset
        from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
        from magic_pdf.config.enums import SupportedPdfParseMethod
    except ImportError as e:
        print(f"ERROR: magic-pdf not available in this environment: {e}", file=sys.stderr)
        return 1

    pdf_stem = pdf_path.stem
    result_dir = output_dir / pdf_stem
    result_dir.mkdir(parents=True, exist_ok=True)

    images_dir = result_dir / "images"
    images_dir.mkdir(exist_ok=True)

    print(f"Processing: {pdf_path.name}", file=sys.stderr)
    print(f"Output: {result_dir}", file=sys.stderr)

    # image_dir_prefix is the relative prefix embedded into markdown/content_list
    # for image paths. "images" means images appear as "images/<filename>" in output.
    image_dir_prefix = "images"

    try:
        reader = FileBasedDataReader("")
        pdf_bytes = reader.read(str(pdf_path))

        ds = PymuDocDataset(pdf_bytes)
        image_writer = FileBasedDataWriter(str(images_dir))

        # Use auto mode — picks txt or ocr based on content
        if ds.classify() == SupportedPdfParseMethod.TXT:
            print("Mode: TXT", file=sys.stderr)
            infer_result = ds.apply(doc_analyze, ocr=False)
            pipe_result = infer_result.pipe_txt_mode(image_writer)
        else:
            print("Mode: OCR", file=sys.stderr)
            infer_result = ds.apply(doc_analyze, ocr=True)
            pipe_result = infer_result.pipe_ocr_mode(image_writer)

        # ── Write markdown ────────────────────────────────────────────────────
        md_filename = f"{pdf_stem}.md"
        pipe_result.dump_md(
            FileBasedDataWriter(str(result_dir)),
            md_filename,
            image_dir_prefix,
        )

        # ── Write content list JSON ───────────────────────────────────────────
        # get_content_list returns a JSON *string* (not a list) in the new API.
        content_list_raw = pipe_result.get_content_list(image_dir_prefix)
        if isinstance(content_list_raw, str):
            content_list = json.loads(content_list_raw)
        else:
            # Older API returned a list directly — handle both
            content_list = content_list_raw

        cl_path = result_dir / f"{pdf_stem}_content_list.json"
        with open(cl_path, "w", encoding="utf-8") as f:
            json.dump(content_list, f, ensure_ascii=False, indent=2)

        print(f"SUCCESS: {len(content_list)} content blocks written.", file=sys.stderr)
        print(f"Content list: {cl_path}", file=sys.stderr)
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
