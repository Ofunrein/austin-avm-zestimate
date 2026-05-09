#!/usr/bin/env python3
"""
Download Redfin Austin bulk CSV, batch-predict all listings, upsert into predictions table.

Usage:
  SUPABASE_URL=... SUPABASE_KEY=... API_BASE=https://ofunrein-austin-avm-api.hf.space \
    python -m api.scripts.seed_inventory

The Redfin URL occasionally changes. If it fails, download the Austin CSV manually from:
  https://www.redfin.com/news/data-center/
and pass it as: python -m api.scripts.seed_inventory --csv /path/to/austin.csv
"""
import argparse
import csv
import json
import os
import ssl
import sys
import time
import urllib.request
from pathlib import Path

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

KAGGLE_DATASET = "ericpierce/austinhousingprices"
API_BASE = os.environ.get("API_BASE", "http://localhost:7860")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
MAX_ROWS = int(os.environ.get("SEED_MAX_ROWS", "2000"))


def download_kaggle_csv() -> list[dict]:
    import subprocess, tempfile, glob
    print(f"Downloading Kaggle dataset {KAGGLE_DATASET} ...")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["kaggle", "datasets", "download", "-d", KAGGLE_DATASET, "-p", tmp, "--unzip"],
            check=True,
        )
        csvs = glob.glob(f"{tmp}/*.csv")
        if not csvs:
            raise FileNotFoundError(f"No CSV found in {tmp}")
        with open(csvs[0], newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))


def parse_row(row: dict) -> dict | None:
    try:
        # Kaggle Austin dataset column names
        sqft = float(row.get("livingAreaSqFt") or row.get("SQUARE FEET") or 0)
        if sqft < 200 or sqft > 20000:
            return None
        lat = float(row.get("latitude") or row.get("LATITUDE") or 0)
        lng = float(row.get("longitude") or row.get("LONGITUDE") or 0)
        if not (29.0 <= lat <= 31.5 and -99.0 <= lng <= -96.5):
            return None
        zip_code = str(row.get("zipcode") or row.get("ZIP OR POSTAL CODE") or "")[:5]
        if len(zip_code) != 5:
            return None
        address = (
            row.get("streetAddress") or row.get("ADDRESS") or ""
        ).strip()
        beds = int(float(row.get("numOfBedrooms") or row.get("numBedrooms") or row.get("BEDS") or 0))
        baths = float(row.get("numOfBathrooms") or row.get("numBathrooms") or row.get("BATHS") or 0)
        year = int(float(row.get("yearBuilt") or row.get("YEAR BUILT") or 2000))
        lot = float(row.get("lotSizeSqFt") or row.get("LOT SIZE") or 0)
        price = int(float(row.get("latestPrice") or row.get("PRICE") or 0))
        return {
            "address": address,
            "sqft_living": sqft,
            "beds": beds,
            "baths_full": baths,
            "year_built": year,
            "zip_code": zip_code,
            "lat": lat,
            "lng": lng,
            "lot_sqft": lot,
            "list_price": price,
            "photo_url": (
                f"https://photos.zillowstatic.com/fp/{row['homeImage']}"
                if row.get("homeImage") and str(row.get("homeImage", "")).strip()
                else ""
            ),
        }
    except (ValueError, TypeError):
        return None


def predict_property(prop: dict) -> dict | None:
    payload = {
        k: v for k, v in prop.items()
        if k not in ("address", "list_price", "photo_url")
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API_BASE}/predict",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  predict failed: {e}")
        return None


def upsert_batch(records: list[dict], db) -> None:
    for i in range(0, len(records), 100):
        batch = records[i : i + 100]
        db.table("predictions").upsert(batch, on_conflict="address").execute()
        print(f"  upserted {min(i + 100, len(records))}/{len(records)}")


def main(csv_path: str | None = None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    from supabase import create_client
    db = create_client(SUPABASE_URL, SUPABASE_KEY)

    if csv_path:
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    else:
        rows = download_kaggle_csv()

    print(f"Downloaded {len(rows)} rows. Processing up to {MAX_ROWS}...")

    records: list[dict] = []
    for i, row in enumerate(rows[:MAX_ROWS]):
        parsed = parse_row(row)
        if not parsed:
            continue
        pred = predict_property(parsed)
        if not pred:
            continue
        records.append({
            "address": parsed["address"],
            "lat": parsed["lat"],
            "lng": parsed["lng"],
            "sqft_living": parsed["sqft_living"],
            "beds": parsed["beds"],
            "baths_full": parsed["baths_full"],
            "year_built": parsed["year_built"],
            "zip_code": parsed["zip_code"],
            "predicted_price": pred["predicted_price"],
            "lower_bound": pred["lower_bound"],
            "upper_bound": pred["upper_bound"],
            "confidence_score": pred["confidence_score"],
            "shap_json": pred["shap_top5"],
            "list_price": parsed["list_price"],
            "photo_url": parsed.get("photo_url", ""),
            "data_source": "kaggle_historical",
        })
        if (i + 1) % 50 == 0:
            print(f"  processed {i + 1}/{min(MAX_ROWS, len(rows))}")
        time.sleep(0.05)

    print(f"Upserting {len(records)} records...")
    upsert_batch(records, db)
    print("Seed complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=None, help="Path to local Redfin CSV")
    args = parser.parse_args()
    main(csv_path=args.csv)
