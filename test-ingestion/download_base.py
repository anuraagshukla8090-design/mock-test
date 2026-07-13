from huggingface_hub import snapshot_download
import os

models_dir = os.path.join(os.getcwd(), 'magic-pdf-models')
os.makedirs(models_dir, exist_ok=True)

patterns = [
    "models/MFR/unimernet_base/*",
    "models/MFR/UniMERNet/*",
]

print("Downloading the 3.5GB base models from HuggingFace...")
snapshot_download(
    repo_id='opendatalab/PDF-Extract-Kit-1.0', 
    local_dir=models_dir,
    allow_patterns=patterns
)
print("Base model download complete!")
