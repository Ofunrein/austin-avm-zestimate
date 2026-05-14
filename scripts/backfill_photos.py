#!/usr/bin/env python3
"""
Backfill photo_url for predictions rows that have dead/missing Zillow images.
Usage:
    SUPABASE_URL=... SUPABASE_KEY=... APIFY_API_TOKEN=... python3 scripts/backfill_photos.py
"""
import os
import time
import urllib.parse

import requests

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
APIFY_TOKEN  = os.environ["APIFY_API_TOKEN"]
ACTOR_URL = (
    "https://api.apify.com/v2/acts/maxcopell~zillow-detail-scraper"
    f"/run-sync-get-dataset-items?token={APIFY_TOKEN}&timeout=60&memory=1024"
)
SB_HDR = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def is_dead(url):
    if not url:
        return True
    return "zillowstatic.com/fp/" in url and url.endswith("_p_f.jpg")


def scrape_image(address: str):
    for status in ("FOR_SALE", "RECENTLY_SOLD"):
        try:
            r = requests.post(ACTOR_URL, json={"addresses": [address], "propertyStatus": status}, timeout=70)
            items = r.json()
            if not isinstance(items, list) or not items:
                continue
            item = items[0]
            img = (
                (item.get("responsivePhotos") or [{}])[0].get("url")
                or item.get("hiResImageLink")
                or item.get("imgSrc")
            )
            if img and isinstance(img, str) and img.startswith("http"):
                return img
        except Exception as e:
            print(f"  [{status}] error: {e}")
    return None


def main():
    rows = requests.get(
        f"{SUPABASE_URL}/rest/v1/predictions?select=address,photo_url&limit=200&order=id",
        headers=SB_HDR,
    ).json()
    need = [r for r in rows if is_dead(r.get("photo_url"))]
    print(f"{len(need)} rows to backfill (of {len(rows)} total)")

    for i, row in enumerate(need):
        addr = row["address"]
        print(f"[{i+1}/{len(need)}] {addr}")
        img = scrape_image(addr)
        if img:
            enc = urllib.parse.quote(addr, safe="")
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/predictions?address=eq.{enc}",
                json={"photo_url": img},
                headers={**SB_HDR, "Prefer": "return=minimal"},
            )
            print(f"  → {img[:80]}")
        else:
            print("  → no image found")
        time.sleep(0.5)

    print("Done.")


if __name__ == "__main__":
    main()
