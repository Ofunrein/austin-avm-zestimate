import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import httpx

# TEA school district accountability ratings by Austin ZIP (2023)
# Source: tea.texas.gov — A=exemplary, B=recognized, C=acceptable, D/F=needs improvement
_AUSTIN_SCHOOL_RATINGS: dict[str, str] = {
    "78701": "C", "78702": "C", "78703": "C", "78704": "C",
    "78705": "C", "78721": "C", "78722": "C", "78723": "C",
    "78724": "C", "78725": "C", "78726": "B", "78727": "B",
    "78728": "B", "78729": "B", "78730": "B", "78731": "B",
    "78732": "B", "78733": "B", "78734": "B", "78735": "B",
    "78736": "B", "78737": "B", "78738": "B", "78739": "B",
    "78741": "C", "78742": "C", "78744": "C", "78745": "C",
    "78746": "A", "78747": "B", "78748": "B", "78749": "B",
    "78750": "A", "78751": "C", "78752": "C", "78753": "C",
    "78754": "C", "78756": "C", "78757": "C", "78758": "C",
    "78759": "B",
}


def _fetch_walkscore(zip_code: str, lat: float, lng: float) -> dict:
    key = os.environ.get("WALKSCORE_API_KEY", "")
    if not key:
        return {"walk_score": None, "transit_score": None, "bike_score": None}
    try:
        r = httpx.get(
            "https://api.walkscore.com/score",
            params={
                "format": "json",
                "address": f"{zip_code} Austin TX",
                "lat": lat,
                "lon": lng,
                "transit": 1,
                "bike": 1,
                "wsapikey": key,
            },
            timeout=5.0,
        )
        data = r.json()
        return {
            "walk_score": data.get("walkscore"),
            "transit_score": (data.get("transit") or {}).get("score"),
            "bike_score": (data.get("bike") or {}).get("score"),
        }
    except Exception:
        return {"walk_score": None, "transit_score": None, "bike_score": None}


def _fetch_census_income(zip_code: str) -> dict:
    try:
        r = httpx.get(
            "https://api.census.gov/data/2022/acs/acs5",
            params={
                "get": "B19013_001E,B01003_001E",
                "for": f"zip code tabulation area:{zip_code}",
            },
            timeout=8.0,
        )
        rows = r.json()
        if len(rows) < 2:
            return {"median_income": None, "population": None}
        values = rows[1]
        income = int(values[0]) if values[0] and values[0] != "-666666666" else None
        pop = int(values[1]) if values[1] else None
        return {"median_income": income, "population": pop}
    except Exception:
        return {"median_income": None, "population": None}


def _fetch_crime(zip_code: str) -> dict:
    try:
        cutoff = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S")
        r = httpx.get(
            "https://data.austintexas.gov/resource/fdj4-gpfu.json",
            params={
                "$where": f"zip_code='{zip_code}' AND occurred_time >= '{cutoff}'",
                "$select": "count(*) AS total",
            },
            timeout=8.0,
        )
        data = r.json()
        total = int(data[0]["total"]) if data and "total" in data[0] else 0
        return {"crime_incidents": total}
    except Exception:
        return {"crime_incidents": None}


def fetch_neighborhood(zip_code: str, lat: float = 30.27, lng: float = -97.74) -> dict:
    school_rating = _AUSTIN_SCHOOL_RATINGS.get(zip_code, "N/A")

    with ThreadPoolExecutor(max_workers=3) as pool:
        ws_f = pool.submit(_fetch_walkscore, zip_code, lat, lng)
        census_f = pool.submit(_fetch_census_income, zip_code)
        crime_f = pool.submit(_fetch_crime, zip_code)
        ws = ws_f.result()
        census = census_f.result()
        crime = crime_f.result()

    pop = census.get("population")
    income = census.get("median_income")
    walk = ws.get("walk_score")
    transit = ws.get("transit_score")
    bike = ws.get("bike_score")
    crime_total = crime.get("crime_incidents")

    density = round(pop / 15, 0) if pop else None
    crime_per_1k = round(crime_total / pop * 1000, 1) if (crime_total and pop) else None

    parts: list[str] = []
    if walk is not None:
        label = (
            "Walker's Paradise" if walk >= 90
            else "Very Walkable" if walk >= 70
            else "Somewhat Walkable" if walk >= 50
            else "Car-Dependent"
        )
        parts.append(f"Walk Score {walk} ({label})")
    if school_rating != "N/A":
        parts.append(f"school rating {school_rating} (TEA)")
    if income:
        parts.append(f"median income ${income // 1000}k")
    if crime_per_1k is not None:
        label = "low" if crime_per_1k < 20 else "average" if crime_per_1k < 40 else "above-average"
        parts.append(f"{label} crime ({crime_per_1k}/1k)")

    return {
        "zip_code": zip_code,
        "school_rating": school_rating,
        "walk_score": walk,
        "transit_score": transit,
        "bike_score": bike,
        "median_income": income,
        "population_density": density,
        "crime_incidents_per_1k": crime_per_1k,
        "summary": ", ".join(parts) if parts else "Neighborhood data unavailable",
    }
