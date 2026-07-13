"""
ocr_answer_key.py

Subprocess helper: runs MinerU's built-in OCR engine on a single image
(the answer key crop saved by LayoutLMv3) and extracts answer entries.

Usage:
    .venv310/Scripts/python.exe scripts/ocr_answer_key.py --image <path>

Output (stdout): JSON  {"text": "<raw ocr text joined by spaces>"}
Exit 0 on success, 1 on error (stderr has details).

Strategy:
  1. Preprocess the image: convert to grayscale, remove watermarks (light-blue
     semi-transparent elements) by thresholding, boost contrast.
  2. Run MinerU's PytorchPaddleOCR (ch_lite — weights are present) on the
     cleaned image.
  3. Join all detected text fragments in left-to-right, top-to-bottom reading
     order (sorted by bounding box Y then X).
  4. Output raw joined text for the calling process to parse with _ANS_ENTRY_RE.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR an answer-key image.")
    parser.add_argument("--image", required=True, help="Absolute path to the image file.")
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"ERROR: image not found: {img_path}", file=sys.stderr)
        return 1

    try:
        import cv2
        import numpy as np
        from magic_pdf.model.sub_modules.ocr.paddleocr2pytorch.pytorch_paddle import PytorchPaddleOCR

        # ── Load image ────────────────────────────────────────────────────────
        img = cv2.imread(str(img_path))
        if img is None:
            from PIL import Image
            pil_img = Image.open(img_path).convert("RGB")
            img = np.array(pil_img)[:, :, ::-1]  # RGB → BGR

        # ── Preprocess: strip watermarks + boost contrast ──────────────────
        # MathonGo watermarks are light-blue (~RGB 173,216,230) semi-transparent.
        # Convert to grayscale and apply CLAHE to boost contrast so OCR
        # cleanly reads the bold black answer numbers.
        img_preprocessed = _preprocess(img)

        # ── Run OCR ───────────────────────────────────────────────────────────
        # ch_lite: uses ch_PP-OCRv5_det_infer.pth (present locally).
        # en_PP-OCRv3_det_infer.pth is missing, so we avoid lang="en".
        # ch_lite reliably detects printed digits and punctuation.
        ocr = PytorchPaddleOCR(lang="ch_lite")
        raw_results = ocr.ocr(img_preprocessed, det=True, rec=True)

        # ── Flatten and sort by reading order (top→bottom, left→right) ───────
        text_fragments: list[tuple[float, float, str]] = []
        if raw_results and raw_results[0]:
            for item in raw_results[0]:
                if not item or len(item) < 2:
                    continue
                box, text_info = item[0], item[1]
                if isinstance(text_info, (list, tuple)):
                    text = str(text_info[0])
                    conf = float(text_info[1]) if len(text_info) > 1 else 1.0
                else:
                    text = str(text_info)
                    conf = 1.0

                # Skip very low confidence or very short fragments
                if conf < 0.3 or len(text.strip()) < 1:
                    continue

                # Bounding box centroid for sort
                pts = np.array(box)
                cy = float(pts[:, 1].mean())
                cx = float(pts[:, 0].mean())
                text_fragments.append((cy, cx, text.strip()))

        # Sort top→bottom, left→right
        text_fragments.sort(key=lambda t: (round(t[0] / 20) * 20, t[1]))
        joined = " ".join(t[2] for t in text_fragments)

        print(json.dumps({"text": joined}))
        print(f"OCR extracted {len(text_fragments)} fragments", file=sys.stderr)
        return 0

    except Exception as exc:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _preprocess(img):
    """
    Convert to grayscale + CLAHE contrast boost to help OCR read
    printed text through semi-transparent watermarks.
    Returns a grayscale numpy array (single channel).
    """
    import cv2
    import numpy as np

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # CLAHE: boosts local contrast (helps with faint text)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Otsu binarization: turns the image into clean black-on-white
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Convert back to BGR so PaddleOCR accepts it
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


if __name__ == "__main__":
    sys.exit(main())
