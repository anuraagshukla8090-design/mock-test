# MinerU (Magic-PDF) — Evaluation PoC

> **Scope**: Completely isolated benchmark.
> Your existing pipeline is untouched.

---

## Purpose

Determine whether MinerU can improve:

| Weakness | What MinerU offers |
|---|---|
| Figure extraction | Every figure → individual PNG, referenced in Markdown |
| Formula extraction | Native LaTeX output (`$...$` / `$$...$$`) |
| Reading order | Layout-model that handles multi-column sheets |

---

## Folder Structure

```
mineru-test/
├── input/
│   ├── physics.pdf          ← put your ALLEN / JEE / NEET PDFs here
│   ├── chemistry.pdf
│   └── maths.pdf
│
├── output/
│   ├── physics/
│   │   ├── physics.md                ← full document Markdown
│   │   ├── physics_content_list.json ← flat reading-order list
│   │   ├── physics_middle.json       ← full parse tree
│   │   ├── physics_layout.pdf        ← colour-coded layout debug
│   │   ├── physics_span.pdf          ← span-level debug
│   │   └── images/
│   │       ├── physics_0_img_0.png   ← extracted figures
│   │       └── …
│   ├── chemistry/  (same structure)
│   ├── maths/      (same structure)
│   └── _reports/
│       └── evaluation_report.md      ← auto-generated report
│
├── scripts/
│   └── run_mineru.py        ← main evaluation script
│
├── requirements.txt
└── README.md                ← this file
```

---

## Step-by-Step Setup

### 1 — Create a virtual environment (Python 3.10 recommended)

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3.10 -m venv .venv
source .venv/bin/activate
```

> **Why Python 3.10?**
> MinerU's model dependencies (detectron2, etc.) have the most stable
> pre-built wheels for Python 3.10. 3.11–3.13 work but may require
> compiling from source.

---

### 2 — Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> On first run `magic-pdf` will attempt to download its model weights
> (~1-3 GB). Ensure you have a stable internet connection.

#### GPU users (CUDA)

Replace `magic-pdf[full-cpu]` in `requirements.txt` with:

```
magic-pdf[full]
```

Then install the matching torch + CUDA build per the
[MinerU GPU guide](https://github.com/opendatalab/MinerU#gpu).

---

### 3 — Configure magic-pdf models

MinerU stores its configuration in `~/magic-pdf.json`.
After the first `pip install`, run:

```bash
magic-pdf --version
```

This creates the default config file. Then open
`C:\Users\<YourName>\magic-pdf.json` (Windows) and confirm
`models-dir` points to where weights were downloaded, e.g.:

```json
{
  "models-dir": "C:/Users/<YourName>/magic-pdf-models",
  "device-mode": "cpu"
}
```

---

### 4 — Add your PDFs

Copy your coaching-institute PDFs into `input/`:

```
mineru-test/input/physics.pdf
mineru-test/input/chemistry.pdf
mineru-test/input/maths.pdf
```

Any filename works — the script processes every `*.pdf` in that folder.

---

### 5 — Run the evaluation

```bash
# From the mineru-test/ directory:
python scripts/run_mineru.py
```

The script will:

1. Discover all PDFs in `input/`
2. Run the full MinerU pipeline on each (TXT parse-mode — best for born-digital PDFs)
3. Write all artefacts to `output/<pdf-stem>/`
4. Print a summary table in the terminal
5. Write `output/_reports/evaluation_report.md`

---

## Output Files — Explained

| File | What it is |
|---|---|
| `<stem>.md` | Full document as Markdown. Contains text, LaTeX formulas, Markdown tables, and `![](images/…)` figure links. |
| `<stem>_content_list.json` | Flat JSON list of content blocks **in reading order**. Each block has `type`, `text`/`img_path`/`table_body`, `page_idx`, and `bbox`. |
| `<stem>_middle.json` | Rich intermediate parse tree: page → para_blocks → lines → spans. Use this for sub-line precision or custom DB ingestion. |
| `<stem>_layout.pdf` | Debug PDF: coloured rectangles over every detected region. Numbers in top-right show reading order. |
| `<stem>_span.pdf` | Debug PDF: span-level text segmentation. Use to verify inline formula boundary detection. |
| `images/<stem>_<page>_<idx>.png` | Every extracted figure / diagram / graph as a standalone PNG. |

---

## Evaluation Report

Open `output/_reports/evaluation_report.md` after running.

It answers all 13 evaluation questions for every PDF including:

- Content block counts
- LaTeX formula count
- Table count
- Figure count
- Processing time
- Output folder size
- Bonus: JSON schema documentation
- Bonus: React rendering guide
- Bonus: Figure linkage explanation
- Final recommendation (MinerU vs PyMuPDF)

---

## Key Decision: TXT vs OCR Parse Mode

The script uses **TXT mode** by default.

| Mode | When to use |
|---|---|
| `TXT` (default) | Born-digital PDFs (ALLEN, Aakash, PW — not scanned) |
| `OCR` | Scanned / photographed PDFs only |

To switch to OCR mode, change this line in `run_mineru.py`:

```python
# Line ~130 in process_pdf()
infer_result = ds.apply(doc_analyze, ocr=False)   # TXT mode (default)
infer_result = ds.apply(doc_analyze, ocr=True)    # OCR mode
```

---

## Hardware Notes

| Hardware | Expected speed |
|---|---|
| CPU only | ~30-120 s per page |
| NVIDIA GPU (CUDA) | ~3-15 s per page |
| Apple Silicon (MPS) | ~10-30 s per page |

For evaluation, CPU is sufficient.
For production integration, GPU is strongly recommended.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ImportError: magic_pdf` | Run `pip install magic-pdf[full-cpu]` inside the activated venv |
| `models-dir not found` | Run `magic-pdf --version` once to generate `~/magic-pdf.json`, then verify path |
| Empty `images/` folder | Ensure PDF contains actual embedded images (not just CSS backgrounds) |
| Garbled formulas | Try `ocr=True` for pages with image-rendered math |
| `detectron2` build error | Use Python 3.10 and pre-built wheels from MinerU releases page |
