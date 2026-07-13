from huggingface_hub import snapshot_download
import os

models_dir = os.path.join(os.getcwd(), 'magic-pdf-models')
os.makedirs(models_dir, exist_ok=True)

# We only download models for layout, formulas (MFD/MFR), TabRec (tables), and reading order.
# We exclude OCR models to save a massive amount of download size.
patterns = [
    "models/MFD/YOLO/*",
    "models/MFR/*small*/*",
    "models/Layout/YOLO/*",
    "models/ReadingOrder/*", 
    "models/OCR/*",
    "models/TabRec/*",
]

print("Downloading minimal MinerU models from HuggingFace...")
snapshot_download(
    repo_id='opendatalab/PDF-Extract-Kit-1.0', 
    local_dir=models_dir,
    allow_patterns=patterns
)
print("Minimal download complete!")
