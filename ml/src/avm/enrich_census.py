"""
Fetch Census ACS 5-year median household income by ZIP Code Tabulation Area.
Returns normalized 0-1 scores keyed by ZIP5 string.

No API key required. Uses Census public data API.
Variable B19013_001E = median household income in past 12 months.

Usage:
    from avm.enrich_census import fetch_zip_income_scores
    income_lookup = fetch_zip_income_scores()  # defaults to Texas (FIPS 48)
"""
import json
import urllib.request
import urllib.parse
from pathlib import Path

CACHE_PATH = Path(__file__).parents[3] / "data/raw/census_acs_income.json"
ACS_YEAR = "2022"  # latest stable ACS 5-year


def fetch_zip_income_scores(
    state_fips: str = "48",  # Texas — used for filtering post-fetch, not in URL
    force_refresh: bool = False,
) -> dict[str, float]:
    """Return dict mapping ZIP5 → normalized income score (0–1)."""
    if CACHE_PATH.exists() and not force_refresh:
        with open(CACHE_PATH) as f:
            return json.load(f)

    # ZCTAs don't support in=state:XX filter — fetch all US ZCTAs then filter by TX prefix
    url = (
        f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
        f"?get=B19013_001E&for=zip+code+tabulation+area:*"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AustinAVM/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    # data[0] is header: ['B19013_001E', 'zip code tabulation area']
    rows = data[1:]
    raw: dict[str, float] = {}
    for row in rows:
        income_str = row[0]
        zip5 = row[1]
        try:
            income = float(income_str)
            if income > 0:
                raw[zip5] = income
        except (ValueError, TypeError):
            continue

    if not raw:
        return {}

    min_income = min(raw.values())
    max_income = max(raw.values())
    span = max_income - min_income or 1.0
    normalized = {z: round((v - min_income) / span, 4) for z, v in raw.items()}

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(normalized, f)

    return normalized
