"""
Property lookup endpoint — geocodes an address and attempts to fetch
property details (sqft, beds, baths, year built) from Zillow via Apify.

Env vars:
  APIFY_API_TOKEN  — Apify token (optional; skips enrichment if missing)
  SUPABASE_URL     — Supabase project URL
  SUPABASE_KEY     — Supabase service role key
"""
import json
import os
import urllib.request
import urllib.parse
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

ACTOR_ID = "maxcopell~zillow-scraper"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


def _apify_token() -> str:
    return os.environ.get("APIFY_API_TOKEN", "")


class LookupRequest(BaseModel):
    address: str


class LookupResponse(BaseModel):
    address_normalized: str | None = None
    zip_code: str | None = None
    lat: float | None = None
    lng: float | None = None
    sqft_living: float | None = None
    beds: int | None = None
    baths_full: float | None = None
    year_built: int | None = None
    image_url: str | None = None
    source: str = "geocode_only"


def _is_dead_photo_url(url: str | None) -> bool:
    """Old Kaggle homeImage format OR missing — need fresh Apify image."""
    if not url:
        return True
    return "zillowstatic.com/fp/" in url and url.endswith("_p_f.jpg")


def _patch_supabase_photo(address: str, photo_url: str) -> None:
    """Write fresh photo_url back to predictions table."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        encoded = urllib.parse.quote(address)
        url = f"{SUPABASE_URL}/rest/v1/predictions?address=eq.{encoded}"
        payload = json.dumps({"photo_url": photo_url}).encode()
        req = urllib.request.Request(url, data=payload, method="PATCH", headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        })
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass
    """Check predictions table for cached property data."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        encoded = urllib.parse.quote(address)
        url = f"{SUPABASE_URL}/rest/v1/predictions?address=eq.{encoded}&select=sqft_living,beds,baths_full,year_built,zip_code,lat,lng,photo_url&limit=1"
        req = urllib.request.Request(url, headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            rows = json.loads(resp.read())
        if not rows:
            return None
        row = rows[0]
        if not any([row.get("sqft_living"), row.get("beds"), row.get("baths_full")]):
            return None
        return {
            "sqft_living": row.get("sqft_living"),
            "beds": row.get("beds"),
            "baths_full": row.get("baths_full"),
            "year_built": row.get("year_built"),
            "image_url": row.get("photo_url") or None,
        }
    except Exception:
        return None


def _nominatim_geocode(address: str) -> dict | None:
    query = address if ("Austin" in address or "TX" in address) else f"{address}, Austin, TX"
    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?q={urllib.parse.quote(query)}&format=json&addressdetails=1&limit=1&countrycodes=us"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AustinAVM/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if not data:
            return None
        r = data[0]
        lat = float(r["lat"])
        lng = float(r["lon"])
        if not (29.0 <= lat <= 31.5 and -99.0 <= lng <= -96.5):
            return None
        return {
            "lat": lat,
            "lng": lng,
            "zip_code": r.get("address", {}).get("postcode", "")[:5],
            "display": r.get("display_name", ""),
        }
    except Exception:
        return None


def _census_geocode(address: str) -> dict | None:
    """US Census Bureau geocoder — better coverage for newer TX streets."""
    query = address if ("Austin" in address or "TX" in address) else f"{address}, Austin, TX"
    url = (
        "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
        f"?address={urllib.parse.quote(query)}&benchmark=2020&format=json"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AustinAVM/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        matches = data.get("result", {}).get("addressMatches", [])
        if not matches:
            return None
        m = matches[0]
        coords = m.get("coordinates", {})
        lat = float(coords.get("y", 0))
        lng = float(coords.get("x", 0))
        if not (29.0 <= lat <= 31.5 and -99.0 <= lng <= -96.5):
            return None
        components = m.get("addressComponents", {})
        zip_code = components.get("zip", "")[:5]
        return {
            "lat": lat,
            "lng": lng,
            "zip_code": zip_code,
            "display": m.get("matchedAddress", address),
        }
    except Exception:
        return None


def _apify_zillow_lookup(address: str) -> dict | None:
    token = _apify_token()
    if not token:
        return None
    url = (
        "https://api.apify.com/v2/acts/maxcopell~zillow-detail-scraper/run-sync-get-dataset-items"
        f"?token={token}&timeout=30&memory=256"
    )
    for status in ("FOR_SALE", "RECENTLY_SOLD"):
        try:
            payload = json.dumps({"addresses": [address], "propertyStatus": status}).encode()
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=35) as resp:
                items = json.loads(resp.read())
            if not items:
                continue
            item = items[0]
            sqft = item.get("livingArea") or item.get("livingAreaValue")
            beds = item.get("bedrooms") or item.get("beds")
            baths = item.get("bathrooms") or item.get("baths")
            year = item.get("yearBuilt")
            if not any([sqft, beds, baths, year]):
                continue
            # Prefer responsivePhotos[0].url — direct CDN link confirmed live
            img = (
                ((item.get("responsivePhotos") or [{}])[0].get("url"))
                or item.get("hiResImageLink")
                or item.get("desktopWebHdpImageLink")
                or item.get("imgSrc")
                or (item.get("responsivePhotos") or [{}])[0].get("mixedSources", {}).get("jpeg", [{}])[-1].get("url")
            )
            return {
                "sqft_living": float(sqft) if sqft else None,
                "beds": int(beds) if beds else None,
                "baths_full": float(baths) if baths else None,
                "year_built": int(year) if year else None,
                "image_url": img if isinstance(img, str) and img.startswith("http") else None,
            }
        except Exception as e:
            print(f"  apify {status} failed: {e}")
            continue
    return None


@router.post("/property-lookup", response_model=LookupResponse)
def property_lookup(req: LookupRequest):
    geo = _nominatim_geocode(req.address) or _census_geocode(req.address)
    if not geo:
        return LookupResponse(source="not_found")

    result = LookupResponse(
        address_normalized=geo["display"],
        zip_code=geo["zip_code"],
        lat=geo["lat"],
        lng=geo["lng"],
        source="geocode_only",
    )

    # Check Supabase cache first (seeded Kaggle properties)
    cached = _supabase_lookup(req.address)
    if cached:
        result.sqft_living = cached.get("sqft_living")
        result.beds = cached.get("beds")
        result.baths_full = cached.get("baths_full")
        result.year_built = cached.get("year_built")
        cached_img = cached.get("image_url")
        # Dead Kaggle URL — fetch a fresh one from Apify and write it back
        if _is_dead_photo_url(cached_img):
            enriched = _apify_zillow_lookup(req.address)
            fresh_img = enriched.get("image_url") if enriched else None
            if fresh_img:
                _patch_supabase_photo(req.address, fresh_img)
                cached_img = fresh_img
        result.image_url = cached_img
        result.source = "supabase_cache"
        return result

    # Fallback to Apify Zillow scraper
    enriched = _apify_zillow_lookup(req.address)
    if enriched:
        result.sqft_living = enriched.get("sqft_living")
        result.beds = enriched.get("beds")
        result.baths_full = enriched.get("baths_full")
        result.year_built = enriched.get("year_built")
        result.image_url = enriched.get("image_url")
        result.source = "zillow"

    return result
