"""
Property lookup endpoint — geocodes an address and attempts to fetch
property details (sqft, beds, baths, year built) from Zillow via Apify.

Env vars:
  APIFY_API_TOKEN  — Apify token (optional; skips enrichment if missing)
"""
import json
import os
import urllib.request
import urllib.parse
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
# apify/zillow-scraper — search by address, returns property details
ACTOR_ID = "apify~zillow-scraper"


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
    source: str = "geocode_only"


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


def _apify_zillow_lookup(address: str) -> dict | None:
    if not APIFY_TOKEN:
        return None
    payload = json.dumps({
        "searchTerm": address,
        "maxItems": 1,
        "extractPropertyDetails": True,
    }).encode()
    url = (
        f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
        f"?token={APIFY_TOKEN}&timeout=25&memory=256"
    )
    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            items = json.loads(resp.read())
        if not items:
            return None
        item = items[0]
        sqft = item.get("livingArea") or item.get("livingAreaValue")
        beds = item.get("bedrooms") or item.get("beds")
        baths = item.get("bathrooms") or item.get("baths")
        year = item.get("yearBuilt")
        if not any([sqft, beds, baths, year]):
            return None
        return {
            "sqft_living": float(sqft) if sqft else None,
            "beds": int(beds) if beds else None,
            "baths_full": float(baths) if baths else None,
            "year_built": int(year) if year else None,
        }
    except Exception:
        return None


@router.post("/property-lookup", response_model=LookupResponse)
def property_lookup(req: LookupRequest):
    geo = _nominatim_geocode(req.address)
    if not geo:
        return LookupResponse(source="not_found")

    result = LookupResponse(
        address_normalized=geo["display"],
        zip_code=geo["zip_code"],
        lat=geo["lat"],
        lng=geo["lng"],
        source="geocode_only",
    )

    enriched = _apify_zillow_lookup(req.address)
    if enriched:
        result.sqft_living = enriched.get("sqft_living")
        result.beds = enriched.get("beds")
        result.baths_full = enriched.get("baths_full")
        result.year_built = enriched.get("year_built")
        result.source = "zillow"

    return result
