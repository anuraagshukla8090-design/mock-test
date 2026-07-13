import os
import time
from huggingface_hub import hf_hub_download, HfApi

models_dir = os.path.join(os.getcwd(), 'magic-pdf-models')
os.makedirs(models_dir, exist_ok=True)

patterns = [
    "models/MFD/YOLO/*",
    "models/MFR/*small*/*",
    "models/Layout/YOLO/*",
    "models/ReadingOrder/*", 
    "models/OCR/*",
]

api = HfApi()
repo_id = 'opendatalab/PDF-Extract-Kit-1.0'

print("Fetching file list...")
files = api.list_repo_files(repo_id=repo_id)

import fnmatch
def matches_any(filename, patterns):
    for p in patterns:
        if fnmatch.fnmatch(filename, p):
            return True
    return False

target_files = [f for f in files if matches_any(f, patterns)]
print(f"Found {len(target_files)} files to download.")

for i, f in enumerate(target_files):
    success = False
    while not success:
        try:
            print(f"Downloading [{i+1}/{len(target_files)}]: {f}")
            hf_hub_download(repo_id=repo_id, filename=f, local_dir=models_dir)
            success = True
        except Exception as e:
            print(f"Error downloading {f}: {e}. Retrying in 5 seconds...")
            time.sleep(5)

print("All models downloaded successfully!")
