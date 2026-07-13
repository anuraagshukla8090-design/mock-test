"""
Upload all 3 PDFs to the running API and poll until done.
Run from mocktest/: .venv/Scripts/python scripts/upload_and_test.py
"""
from __future__ import annotations

import sys
import time
import httpx

API = "http://localhost:8000"

PDFS = [
    r"C:\Users\Anurag shukla\Documents\chemistry.pdf",
    r"C:\Users\Anurag shukla\Documents\maths.pdf",
    r"C:\Users\Anurag shukla\Documents\physics.pdf",
]

TERMINAL_STATES = {"SAVED", "FAILED"}
POLL_INTERVAL = 15   # seconds between status checks


def upload(pdf_path: str) -> dict:
    with open(pdf_path, "rb") as f:
        filename = pdf_path.split("\\")[-1]
        resp = httpx.post(
            f"{API}/api/ingestion/upload",
            files={"file": (filename, f, "application/pdf")},
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json()


def poll(ingestion_id: str) -> dict:
    while True:
        resp = httpx.get(f"{API}/api/ingestion/{ingestion_id}/status", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        status = data["status"]
        print(f"  [{ingestion_id[:8]}] {status}", flush=True)
        if status in TERMINAL_STATES:
            return data
        time.sleep(POLL_INTERVAL)


def print_report(data: dict) -> None:
    r = data.get("processing_report") or {}
    print(f"\n{'='*60}")
    print(f"  File   : {data['filename']}")
    print(f"  Status : {data['status']}")
    if data.get("error_message"):
        print(f"  ERROR  : {data['error_message']}")
    if r:
        print(f"  Detected  : {r.get('questions_detected', '?')} questions")
        print(f"  Stored    : {r.get('questions_stored', '?')}")
        print(f"  Skipped   : {r.get('questions_skipped', '?')}")
        print(f"  Ans mapped: {r.get('answers_mapped', '?')}")
        print(f"  Images    : {r.get('images_linked', '?')}")
        print(f"  Time      : {r.get('processing_time_s', '?')}s")
        warnings = r.get("warnings", [])
        if warnings:
            print(f"  Warnings ({len(warnings)}):")
            for w in warnings[:10]:
                print(f"    ⚠ {w}")
            if len(warnings) > 10:
                print(f"    ... and {len(warnings)-10} more")
    print(f"{'='*60}\n")


def main():
    ingestion_ids = []

    # Upload all 3
    print("Uploading PDFs...\n")
    for path in PDFS:
        print(f"  Uploading {path.split(chr(92))[-1]}...")
        try:
            result = upload(path)
            iid = result["id"]
            ingestion_ids.append((path, iid))
            print(f"  → ingestion_id: {iid}")
        except Exception as e:
            print(f"  ✗ Upload failed: {e}")

    if not ingestion_ids:
        print("No uploads succeeded. Exiting.")
        sys.exit(1)

    print(f"\nPolling {len(ingestion_ids)} ingestion(s) every {POLL_INTERVAL}s...\n")

    # Poll all simultaneously (simple round-robin)
    pending = list(ingestion_ids)
    completed = []
    active = {iid: path for path, iid in pending}

    while active:
        done_ids = []
        for iid, path in list(active.items()):
            try:
                resp = httpx.get(f"{API}/api/ingestion/{iid}/status", timeout=10)
                data = resp.json()
                status = data["status"]
                print(f"  [{path.split(chr(92))[-1][:20]:20s}] {status}")
                if status in TERMINAL_STATES:
                    completed.append(data)
                    done_ids.append(iid)
            except Exception as e:
                print(f"  Poll error for {iid[:8]}: {e}")
        for iid in done_ids:
            del active[iid]
        if active:
            print()
            time.sleep(POLL_INTERVAL)

    # Print reports
    print("\n\n📊 PROCESSING REPORTS\n")
    for data in completed:
        print_report(data)

    # Final DB summary
    print("Checking question bank totals...")
    try:
        resp = httpx.get(f"{API}/api/questions/stats", timeout=10)
        stats = resp.json()
        print(f"\n✅ Question Bank Summary:")
        print(f"   Total: {stats['total']}")
        print(f"   By subject: {stats['by_subject']}")
        print(f"   By difficulty: {stats['by_difficulty']}")
        print(f"   By section type: {stats['by_section_type']}")
    except Exception as e:
        print(f"Could not fetch stats: {e}")


if __name__ == "__main__":
    main()
