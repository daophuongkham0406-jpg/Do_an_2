from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "exercises.csv"
OUTPUT_DIR = BASE_DIR / "image" / "flat"
REPORT_PATH = BASE_DIR / "image_download_report.json"
LINKS_PATH = BASE_DIR / "image_download_links.csv"

IMAGE_COLUMNS = ("image_flat_start", "image_flat_peak", "image_flat_main")
HF_DATASETS = ("RepDB/exercise-dataset",)


def collect_image_paths() -> list[str]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        paths: set[str] = set()
        for row in reader:
            for column in IMAGE_COLUMNS:
                value = (row.get(column) or "").strip()
                if value:
                    paths.add(value.replace("\\", "/"))
    return sorted(paths)


def candidate_urls(image_path: str) -> list[str]:
    encoded_path = quote(image_path, safe="/")
    return [
        f"https://huggingface.co/datasets/{dataset}/resolve/main/{encoded_path}"
        for dataset in HF_DATASETS
    ]


def download_one(index: int, total: int, image_path: str) -> dict[str, str]:
    filename = Path(image_path).name
    target = OUTPUT_DIR / filename
    if target.exists() and target.stat().st_size > 0:
        print(f"[{index}/{total}] skip {filename}", flush=True)
        return {"path": image_path, "status": "skipped", "file": str(target)}

    last_error = ""
    for url in candidate_urls(image_path):
        try:
            request = Request(url, headers={"User-Agent": "FIT-ME-local-dataset-downloader/1.0"})
            with urlopen(request, timeout=12) as response:
                data = response.read()
            if not data:
                last_error = "empty response"
                continue
            target.write_bytes(data)
            print(f"[{index}/{total}] ok {filename}", flush=True)
            return {"path": image_path, "status": "downloaded", "file": str(target), "source": url}
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
            time.sleep(0.2)

    print(f"[{index}/{total}] fail {filename}: {last_error}", flush=True)
    return {"path": image_path, "status": "failed", "file": str(target), "error": last_error}


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image_paths = collect_image_paths()
    with LINKS_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("source_url", "target_file", "original_path"))
        writer.writeheader()
        for path in image_paths:
            writer.writerow(
                {
                    "source_url": candidate_urls(path)[0],
                    "target_file": str(OUTPUT_DIR / Path(path).name),
                    "original_path": path,
                }
            )
    if "--links-only" in sys.argv:
        print(json.dumps({"total_referenced_images": len(image_paths), "links_file": str(LINKS_PATH)}, ensure_ascii=False, indent=2))
        return 0

    results = [download_one(index, len(image_paths), path) for index, path in enumerate(image_paths, start=1)]

    summary = {
        "csv": str(CSV_PATH),
        "output_dir": str(OUTPUT_DIR),
        "links_file": str(LINKS_PATH),
        "total_referenced_images": len(image_paths),
        "downloaded": sum(1 for item in results if item["status"] == "downloaded"),
        "skipped_existing": sum(1 for item in results if item["status"] == "skipped"),
        "failed": sum(1 for item in results if item["status"] == "failed"),
        "failed_items": [item for item in results if item["status"] == "failed"],
    }
    REPORT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
