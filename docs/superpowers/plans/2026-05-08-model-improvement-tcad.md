# Model Improvement Plan: TCAD Data Integration + Census ACS Income

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce ensemble MedAPE below 10% (baseline 12.67%) by enriching training data with Travis County Appraisal District (TCAD) bulk property records and replacing the placeholder `zip_income_score=0.5` with real Census ACS median household income.

**Baseline:** XGBoost + LightGBM ensemble, MedAPE 12.67%, 15,151 records, Kaggle `ericpierce/austinhousingprices`, test cutoff `2020-07-01`.

**Expected gains:** TCAD `grade`/`condition` columns (+1–2% MedAPE improvement per prior literature on appraisal-district grade features); real income scores (+0.5–1%); extended 2021+ data via supplemental Kaggle dataset (+0.5%).

**Tech Stack:** Python 3.11+, uv, `requests`, `thefuzz` (fuzzy address match), `rapidfuzz` (faster alternative), `ml/.venv/`

---

## Task 1: Download Travis County CAD Bulk Data

**Files affected:** none (data only)

**Context:** TCAD publishes annual bulk exports at https://www.traviscad.org/appraisaldata/ — free, no account required. The primary residential file is `REAL_ACCT.csv` (~700k rows, ~80 columns). The ZIP file is typically named `CAMA_export.zip` or `tcad_open_data.zip`. The download URL changes each tax year; the stable landing page is:
`https://www.traviscad.org/appraisaldata/`

As a fallback, use the supplemental Kaggle Austin dataset:
`saritasanchez/zillow-listings-in-austin-area-from-aug-2021`
which adds ~5k post-2021 Austin listings and extends temporal coverage.

- [ ] **Step 1: Create destination directory**

```bash
mkdir -p /Users/martinofunrein/Downloads/avm-zestimate/ml/data/raw/tcad
```

- [ ] **Step 2: Download TCAD bulk data**

Navigate to `https://www.traviscad.org/appraisaldata/` and download the current year's residential export. Save as:

```bash
# Manual download — place the zip at:
# ml/data/raw/tcad/tcad_export.zip
# Then unzip:
cd /Users/martinofunrein/Downloads/avm-zestimate/ml/data/raw/tcad
unzip tcad_export.zip
# The CSV of interest is typically: REAL_ACCT.csv or similar
ls *.csv
```

If TCAD site is unavailable, download the supplemental Kaggle dataset instead:

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate
source ml/.venv/bin/activate
kaggle datasets download -d saritasanchez/zillow-listings-in-austin-area-from-aug-2021 \
  -p ml/data/raw/zillow_2021 --unzip
```

- [ ] **Step 3: Inspect TCAD columns**

```bash
source ml/.venv/bin/activate
python3 -c "
import pandas as pd
import glob, os
csvs = glob.glob('ml/data/raw/tcad/*.csv')
for c in csvs:
    df = pd.read_csv(c, nrows=5, low_memory=False)
    print(c, list(df.columns))
"
```

The columns you need are (names vary by year):
- `situs_addr` or `PROP_STR_ADDR` — street address
- `appraised_val` or `TOTAL_APPRAISED_VALUE` — assessed value
- `impr_grade` or `GRADE` — construction grade (A, B, C, D, E, F)
- `impr_condition` or `CONDITION` — physical condition (Excellent/Good/Fair/Poor)
- `eff_yr_blt` or `EFF_YR_BLT` — effective year built (post-remodel)
- `act_yr_blt` or `ACT_YR_BLT` — actual year built
- `situs_zip` or `PROP_ZIP` — ZIP code

---

## Task 2: Add `fetch_tcad` to `ml/src/avm/ingest.py`

**File:** `ml/src/avm/ingest.py`

Add `fetch_tcad` after the existing `save_raw` function. The function downloads TCAD if the CSV is not already present, handles the uncertain filename, and returns a Path. It never raises on network errors — callers check return value.

- [ ] **Step 1: Install `rapidfuzz` (needed for Task 3)**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate/ml
source .venv/bin/activate
uv pip install rapidfuzz
```

Add `rapidfuzz>=3.6` to `pyproject.toml` dependencies.

- [ ] **Step 2: Edit `ml/src/avm/ingest.py`**

Append the following after the existing `save_raw` function (after line 64):

```python
import glob
import urllib.request

TCAD_RAW = RAW / "tcad"
TCAD_LANDING = "https://www.traviscad.org/appraisaldata/"


def _find_tcad_csv(dest: Path) -> Path | None:
    """Return path to the main residential TCAD CSV if it exists."""
    candidates = [
        "REAL_ACCT.csv", "real_acct.csv", "CAMA.csv", "cama.csv",
        "residential.csv", "RESIDENTIAL.csv",
    ]
    for name in candidates:
        p = dest / name
        if p.exists():
            return p
    # fallback: any CSV over 50 MB (the full export is ~200 MB)
    for p in dest.glob("*.csv"):
        if p.stat().st_size > 50 * 1024 * 1024:
            return p
    return None


def fetch_tcad(dest: Path = TCAD_RAW) -> Path | None:
    """
    Return path to TCAD residential CSV.

    Priority:
    1. Already downloaded CSV in dest/
    2. Attempt HTTP download from TCAD open-data page (best-effort)
    3. Return None if unavailable (caller must handle gracefully)

    The TCAD download URL changes annually. This function scrapes the
    appraisal-data landing page for the first .zip link, downloads it,
    and extracts. If parsing fails, returns None without raising.
    """
    dest.mkdir(parents=True, exist_ok=True)

    existing = _find_tcad_csv(dest)
    if existing:
        return existing

    zip_path = dest / "tcad_export.zip"
    if not zip_path.exists():
        try:
            import re
            import urllib.request
            with urllib.request.urlopen(TCAD_LANDING, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            # find first .zip href on the page
            match = re.search(r'href="([^"]+\.zip)"', html, re.IGNORECASE)
            if not match:
                return None
            zip_url = match.group(1)
            if not zip_url.startswith("http"):
                zip_url = "https://www.traviscad.org" + zip_url
            print(f"  Downloading TCAD data from {zip_url} ...")
            urllib.request.urlretrieve(zip_url, zip_path)
        except Exception as exc:
            print(f"  TCAD download failed ({exc}); skipping TCAD enrichment.")
            return None

    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest)
    except Exception as exc:
        print(f"  TCAD unzip failed ({exc}); skipping TCAD enrichment.")
        return None

    return _find_tcad_csv(dest)


def load_tcad(path: Path | None = None) -> pd.DataFrame | None:
    """Load TCAD CSV, normalise column names, return DataFrame or None."""
    if path is None:
        path = fetch_tcad()
    if path is None or not path.exists():
        return None

    df = pd.read_csv(path, low_memory=False, dtype=str)

    # Normalise column names to snake_case
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Map known column aliases to canonical names
    aliases = {
        "situs_addr": "tcad_address",
        "prop_str_addr": "tcad_address",
        "street_address": "tcad_address",
        "appraised_val": "assessed_value",
        "total_appraised_value": "assessed_value",
        "appr_value": "assessed_value",
        "impr_grade": "grade",
        "bldg_class": "grade",
        "impr_condition": "condition",
        "condition_cd": "condition",
        "eff_yr_blt": "effective_year",
        "eff_yr_blt_nbr": "effective_year",
        "act_yr_blt": "year_built_tcad",
        "act_yr_blt_nbr": "year_built_tcad",
        "situs_zip": "zip_code_tcad",
        "prop_zip": "zip_code_tcad",
        "zip": "zip_code_tcad",
        "remodel_yr": "remodel_year",
    }
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})

    # Keep only the columns we care about
    keep = [c for c in [
        "tcad_address", "assessed_value", "grade", "condition",
        "effective_year", "year_built_tcad", "remodel_year", "zip_code_tcad",
    ] if c in df.columns]
    df = df[keep]

    # Numeric coercions
    for col in ["assessed_value", "effective_year", "year_built_tcad", "remodel_year"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["tcad_address"])
    return df
```

---

## Task 3: Add `merge_tcad` to `ml/src/avm/clean.py`

**File:** `ml/src/avm/clean.py`

`merge_tcad` performs fuzzy address matching between the Kaggle sale records and TCAD property records, then left-joins TCAD appraisal attributes onto the sale records. Returns the enriched DataFrame; unmatched rows retain `NaN` for TCAD columns (handled downstream by `add_assessed_features`).

- [ ] **Step 1: Add imports at top of `clean.py`**

After the existing imports, add:

```python
from typing import Optional
```

(No new external imports needed in the file itself — `rapidfuzz` is imported lazily inside the function.)

- [ ] **Step 2: Append `merge_tcad` to `ml/src/avm/clean.py`**

Append after the `data_sha256` function (after line 117):

```python
def _normalise_address_for_match(addr: str) -> str:
    """Aggressive normalisation for fuzzy match: strip unit numbers, punctuation."""
    if not isinstance(addr, str):
        return ""
    addr = _normalise_address(addr)
    # strip unit designators
    addr = re.sub(r"\b(UNIT|APT|STE|#)\s*[\w-]+", "", addr)
    # strip trailing city/state (anything after a comma)
    addr = addr.split(",")[0].strip()
    # keep only alphanumerics and spaces
    addr = re.sub(r"[^A-Z0-9 ]", "", addr)
    addr = re.sub(r"\s+", " ", addr).strip()
    return addr


def merge_tcad(
    kaggle_df: pd.DataFrame,
    tcad_df: pd.DataFrame,
    score_cutoff: int = 88,
) -> pd.DataFrame:
    """
    Left-join TCAD appraisal attributes onto Kaggle sale records via fuzzy
    address matching.

    Parameters
    ----------
    kaggle_df : cleaned Kaggle DataFrame (must have "address" or "streetAddress" column)
    tcad_df   : output of load_tcad() — must have "tcad_address" column
    score_cutoff : minimum rapidfuzz WRatio score (0-100) to accept a match

    Returns
    -------
    kaggle_df with additional columns: assessed_value, grade, condition,
    effective_year, remodel_year (NaN where no match found)
    """
    from rapidfuzz import process as rfprocess, fuzz

    df = kaggle_df.copy()
    tcad = tcad_df.copy()

    # Resolve address column name in kaggle_df
    addr_col = None
    for cand in ["address", "streetAddress", "street_address", "full_address"]:
        if cand in df.columns:
            addr_col = cand
            break
    if addr_col is None:
        # Cannot match — return df unchanged with NaN TCAD columns
        for col in ["assessed_value", "grade", "condition", "effective_year", "remodel_year"]:
            df[col] = np.nan
        return df

    # Build normalised address series for both sides
    df["_k_addr"] = df[addr_col].apply(_normalise_address_for_match)
    tcad["_t_addr"] = tcad["tcad_address"].apply(_normalise_address_for_match)

    # Index TCAD by normalised address for fast lookup
    tcad_indexed = tcad.set_index("_t_addr")
    tcad_choices = list(tcad_indexed.index)

    # Deduplicate TCAD on normalised address (keep first, highest assessed value)
    if "assessed_value" in tcad_indexed.columns:
        tcad_indexed = tcad_indexed.sort_values("assessed_value", ascending=False)
    tcad_indexed = tcad_indexed[~tcad_indexed.index.duplicated(keep="first")]
    tcad_choices = list(tcad_indexed.index)

    tcad_cols = [c for c in ["assessed_value", "grade", "condition",
                              "effective_year", "remodel_year"] if c in tcad_indexed.columns]

    # Batch fuzzy match using rapidfuzz extractOne
    matched_rows = []
    for k_addr in df["_k_addr"]:
        if not k_addr:
            matched_rows.append({c: np.nan for c in tcad_cols})
            continue
        result = rfprocess.extractOne(
            k_addr, tcad_choices, scorer=fuzz.WRatio, score_cutoff=score_cutoff
        )
        if result is None:
            matched_rows.append({c: np.nan for c in tcad_cols})
        else:
            best_key = result[0]
            row = tcad_indexed.loc[best_key, tcad_cols]
            matched_rows.append(row.to_dict() if hasattr(row, "to_dict") else {c: np.nan for c in tcad_cols})

    match_df = pd.DataFrame(matched_rows, index=df.index)

    # Drop any columns that already exist in df to avoid _x/_y conflicts
    for col in tcad_cols:
        if col in df.columns:
            df = df.drop(columns=[col])

    df = pd.concat([df, match_df], axis=1)
    df = df.drop(columns=["_k_addr"], errors="ignore")

    match_rate = match_df["assessed_value"].notna().mean() if "assessed_value" in match_df else 0.0
    print(f"  TCAD merge match rate: {match_rate:.1%} ({match_df['assessed_value'].notna().sum()} / {len(df)} rows)")

    return df
```

---

## Task 4: Add `fetch_census_acs_income` to `ml/src/avm/features.py`

**File:** `ml/src/avm/features.py`

The Census Bureau ACS 5-year estimates (Table B19013, Median Household Income) are available via the public API with no API key for up to 500 rows. ZIP Code Tabulation Areas (ZCTAs) correspond closely to ZIP codes.

- [ ] **Step 1: Append `fetch_census_acs_income` to `ml/src/avm/features.py`**

Append after the `build_feature_matrix` function (after line 124):

```python
import json
import requests
from pathlib import Path as _Path

_CACHE_PATH = _Path(__file__).parents[2] / "data/processed/zip_income.json"
_ACS_URL = (
    "https://api.census.gov/data/2022/acs/acs5"
    "?get=B19013_001E,NAME&for=zip%20code%20tabulation%20area:*"
)


def fetch_census_acs_income(
    zip_codes: list[str],
    cache_path: _Path = _CACHE_PATH,
    force_refresh: bool = False,
) -> dict[str, float]:
    """
    Fetch ACS 5-year median household income for given ZIP codes.

    Returns dict mapping zip_code (str, 5-digit) -> normalised income score [0, 1].
    Uses cached file at data/processed/zip_income.json if present and not force_refresh.

    The Census API requires no key for basic ACS queries. If the request fails,
    returns a dict of 0.5 (neutral) for all requested ZIPs.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists() and not force_refresh:
        with open(cache_path) as f:
            cached = json.load(f)
        # Check if all requested zips are present
        missing = [z for z in zip_codes if z not in cached]
        if not missing:
            return {z: cached[z] for z in zip_codes}

    try:
        resp = requests.get(_ACS_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"  Census ACS fetch failed ({exc}); using neutral income scores.")
        return {z: 0.5 for z in zip_codes}

    # data[0] is header row: ["B19013_001E", "NAME", "zip code tabulation area"]
    headers = data[0]
    income_idx = headers.index("B19013_001E")
    zcta_idx = headers.index("zip code tabulation area")

    raw_incomes: dict[str, float] = {}
    for row in data[1:]:
        zcta = row[zcta_idx]
        val = row[income_idx]
        try:
            income = float(val)
            if income > 0:
                raw_incomes[zcta] = income
        except (TypeError, ValueError):
            pass

    if not raw_incomes:
        return {z: 0.5 for z in zip_codes}

    # Normalise to [0, 1] using min-max across all ZCTAs in the response
    min_inc = min(raw_incomes.values())
    max_inc = max(raw_incomes.values())
    denom = max(max_inc - min_inc, 1.0)
    normalised = {z: (v - min_inc) / denom for z, v in raw_incomes.items()}

    # Persist full national cache (filtered to Travis County ZIPs only for size)
    travis_cache = {z: v for z, v in normalised.items() if z[:3] in ("786", "787")}
    with open(cache_path, "w") as f:
        json.dump(travis_cache, f, indent=2)

    return {z: normalised.get(z, 0.5) for z in zip_codes}
```

---

## Task 5: Update `ml/src/avm/features.py` — extend `FEATURE_COLS`

The new TCAD features `grade_encoded` and `condition_encoded` need to be added to `FEATURE_COLS` and engineered in `add_structural`.

- [ ] **Step 1: Edit `add_structural` in `ml/src/avm/features.py`**

After the `df["lot_to_living_ratio"]` line (approximately line 26), add:

```python
    # TCAD grade encoding (A=6, B=5, C=4, D=3, E=2, F=1, unknown=0)
    grade_map = {"A": 6, "A+": 7, "A-": 5, "B": 4, "B+": 5, "B-": 3,
                 "C": 3, "C+": 4, "C-": 2, "D": 2, "E": 1, "F": 0}
    if "grade" in df.columns:
        df["grade_encoded"] = df["grade"].str.strip().str.upper().map(grade_map).fillna(0).astype(int)
    else:
        df["grade_encoded"] = 0

    # TCAD condition encoding (Excellent=5, Good=4, Average=3, Fair=2, Poor=1)
    cond_map = {"EXCELLENT": 5, "VERY GOOD": 4, "GOOD": 4, "AVERAGE": 3,
                "FAIR": 2, "POOR": 1, "VERY POOR": 1}
    if "condition" in df.columns:
        df["condition_encoded"] = df["condition"].str.strip().str.upper().map(cond_map).fillna(0).astype(int)
    else:
        df["condition_encoded"] = 0

    # TCAD remodel year — encode as years since remodel
    if "remodel_year" in df.columns:
        df["years_since_remodel"] = (2024 - df["remodel_year"].fillna(df["year_built"])).clip(0, 80)
    else:
        df["years_since_remodel"] = df.get("age", 0)
```

- [ ] **Step 2: Edit `FEATURE_COLS` in `ml/src/avm/features.py`**

Replace the existing `FEATURE_COLS` list (lines 108-117) with:

```python
FEATURE_COLS = [
    "sqft_living", "lot_sqft", "beds", "baths_full", "baths_half", "bath_total",
    "year_built", "age", "effective_age", "stories",
    "has_pool", "has_garage", "garage_spaces",
    "sqft_per_bed", "lot_to_living_ratio",
    "dist_downtown_miles", "zip_income_score", "zip_encoded",
    "median_zip_price_90d", "median_zip_ppsf_90d",
    "price_per_sqft_assessed", "assessed_ratio",
    "grade_encoded", "condition_encoded", "years_since_remodel",
    "is_covid_period",
]
```

---

## Task 6: Update `ml/run_training.py`

- [ ] **Step 1: Add imports at top of `run_training.py`**

After the existing `from avm.ingest import load_kaggle_austin` line, add:

```python
from avm.ingest import load_tcad
from avm.clean import merge_tcad
from avm.features import fetch_census_acs_income
```

- [ ] **Step 2: Replace the load+clean block (steps 1-2) in `main()`**

Replace lines 45-59 with:

```python
    # 1. Load + clean
    print("[1/9] Loading data...")
    raw = load_kaggle_austin()
    raw = normalise_kaggle(raw)
    df = clean(raw)
    print(f"  Kaggle clean records: {len(df):,}")

    # TCAD enrichment (optional — skipped gracefully if unavailable)
    tcad_df = load_tcad()
    if tcad_df is not None:
        print(f"  TCAD records loaded: {len(tcad_df):,}")
        df = merge_tcad(df, tcad_df)
        tcad_available = True
    else:
        print("  TCAD data unavailable — proceeding without enrichment.")
        tcad_available = False

    sha = data_sha256(df)
    print(f"  Data SHA256: {sha}")

    # 2. Feature engineering
    print("[2/9] Feature engineering...")
    df = add_structural(df)

    # Real Census ACS income lookup
    zip_codes = df["zip_code"].unique().tolist()
    income_lookup = fetch_census_acs_income(zip_codes)
    n_real = sum(1 for v in income_lookup.values() if v != 0.5)
    print(f"  Income scores loaded: {n_real}/{len(zip_codes)} ZIPs from Census ACS")

    df, zip_encoder = add_location(df, income_lookup=income_lookup)
    df = add_market_features(df)
    df = add_assessed_features(df)
```

- [ ] **Step 3: Update test cutoff and meta version**

Replace:
```python
    train_df, test_df = train_test_split_temporal(df, test_start="2020-07-01")
```
with:
```python
    # Use later cutoff if TCAD data extends coverage to 2021
    test_start = "2021-01-01" if tcad_available else "2020-07-01"
    train_df, test_df = train_test_split_temporal(df, test_start=test_start)
```

Replace:
```python
        "version": "1.0.0",
```
with:
```python
        "version": "1.1.0",
        "tcad_enriched": tcad_available,
```

---

## Task 7: Write Tests

**Files to create:**
- `ml/tests/test_ingest_tcad.py`
- `ml/tests/test_clean_tcad.py`
- `ml/tests/test_features_tcad.py`

- [ ] **Step 1: Create `ml/tests/test_ingest_tcad.py`**

```python
"""Tests for TCAD ingest functions."""
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import avm.ingest as ingest_module
from avm.ingest import load_tcad, _find_tcad_csv


def _write_fake_tcad(tmp_path: Path, rows: int = 5) -> Path:
    csv = tmp_path / "REAL_ACCT.csv"
    lines = ["SITUS_ADDR,APPRAISED_VAL,IMPR_GRADE,IMPR_CONDITION,EFF_YR_BLT,ACT_YR_BLT,SITUS_ZIP"]
    for i in range(rows):
        lines.append(f"100{i} MAIN ST,{200000 + i * 10000},B,GOOD,{2000 + i},{1995 + i},7870{i}")
    csv.write_text("\n".join(lines))
    return csv


def test_find_tcad_csv_finds_real_acct(tmp_path):
    csv = _write_fake_tcad(tmp_path)
    found = _find_tcad_csv(tmp_path)
    assert found == csv


def test_find_tcad_csv_returns_none_when_empty(tmp_path):
    assert _find_tcad_csv(tmp_path) is None


def test_load_tcad_returns_dataframe(tmp_path):
    csv = _write_fake_tcad(tmp_path)
    df = load_tcad(path=csv)
    assert isinstance(df, pd.DataFrame)
    assert "tcad_address" in df.columns
    assert "assessed_value" in df.columns
    assert "grade" in df.columns
    assert "condition" in df.columns


def test_load_tcad_numeric_coercion(tmp_path):
    csv = _write_fake_tcad(tmp_path)
    df = load_tcad(path=csv)
    assert df["assessed_value"].dtype in [float, "float64"]
    assert df["effective_year"].dtype in [float, "float64"]


def test_load_tcad_returns_none_for_missing_path():
    result = load_tcad(path=Path("/nonexistent/path/REAL_ACCT.csv"))
    assert result is None


def test_fetch_tcad_returns_existing_csv(tmp_path):
    csv = _write_fake_tcad(tmp_path)
    # patch TCAD_RAW to tmp_path so fetch_tcad finds the existing file
    with patch.object(ingest_module, "TCAD_RAW", tmp_path):
        result = ingest_module.fetch_tcad(dest=tmp_path)
    assert result == csv


def test_fetch_tcad_returns_none_on_network_failure(tmp_path):
    """fetch_tcad must not raise when network is unavailable."""
    with patch("urllib.request.urlopen", side_effect=OSError("no network")):
        result = ingest_module.fetch_tcad(dest=tmp_path)
    assert result is None
```

- [ ] **Step 2: Create `ml/tests/test_clean_tcad.py`**

```python
"""Tests for merge_tcad."""
import numpy as np
import pandas as pd
import pytest

from avm.clean import merge_tcad, _normalise_address_for_match


def _make_kaggle() -> pd.DataFrame:
    return pd.DataFrame({
        "sale_price": [450000, 380000, 310000],
        "sqft_living": [1800, 1400, 1100],
        "beds": [3, 2, 2],
        "baths_full": [2, 2, 1],
        "year_built": [2005, 1998, 1985],
        "zip_code": ["78701", "78702", "78703"],
        "lat": [30.27, 30.28, 30.26],
        "lng": [-97.74, -97.73, -97.75],
        "sale_date": pd.to_datetime(["2022-01-15", "2022-04-10", "2022-07-20"]),
        "is_covid_period": [0, 0, 0],
        "address": ["123 Main St, Austin, TX", "456 Oak Ave, Austin, TX", "789 Pine Rd, Austin, TX"],
    })


def _make_tcad() -> pd.DataFrame:
    return pd.DataFrame({
        "tcad_address": ["123 MAIN ST", "456 OAK AVE", "789 PINE RD"],
        "assessed_value": [420000.0, 360000.0, 290000.0],
        "grade": ["B", "C", "B"],
        "condition": ["GOOD", "AVERAGE", "GOOD"],
        "effective_year": [2010.0, 2005.0, 1990.0],
        "remodel_year": [2018.0, np.nan, np.nan],
    })


def test_merge_tcad_adds_assessed_value():
    result = merge_tcad(_make_kaggle(), _make_tcad())
    assert "assessed_value" in result.columns
    assert result["assessed_value"].notna().sum() >= 2  # at least 2 of 3 match


def test_merge_tcad_adds_grade_and_condition():
    result = merge_tcad(_make_kaggle(), _make_tcad())
    assert "grade" in result.columns
    assert "condition" in result.columns


def test_merge_tcad_preserves_row_count():
    kaggle = _make_kaggle()
    result = merge_tcad(kaggle, _make_tcad())
    assert len(result) == len(kaggle)


def test_merge_tcad_no_address_col_returns_nan_cols():
    kaggle = _make_kaggle().drop(columns=["address"])
    result = merge_tcad(kaggle, _make_tcad())
    assert "assessed_value" in result.columns
    assert result["assessed_value"].isna().all()


def test_merge_tcad_empty_tcad_returns_nan_cols():
    empty_tcad = pd.DataFrame(columns=["tcad_address", "assessed_value", "grade"])
    result = merge_tcad(_make_kaggle(), empty_tcad)
    assert len(result) == 3
    assert result["assessed_value"].isna().all()


def test_normalise_address_strips_unit():
    assert "UNIT" not in _normalise_address_for_match("123 Main St Unit 4B, Austin TX")


def test_normalise_address_strips_city():
    normed = _normalise_address_for_match("456 Oak Ave, Austin, TX 78701")
    assert "AUSTIN" not in normed
    assert "456" in normed
```

- [ ] **Step 3: Create `ml/tests/test_features_tcad.py`**

```python
"""Tests for TCAD-related feature engineering and Census ACS income lookup."""
import json
import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch

from avm.features import add_structural, build_feature_matrix, FEATURE_COLS, fetch_census_acs_income


def _base_with_tcad() -> pd.DataFrame:
    return pd.DataFrame({
        "sale_price": [450000, 380000],
        "sqft_living": [1800, 1400],
        "lot_sqft": [5000.0, 4000.0],
        "beds": [3, 2],
        "baths_full": [2, 2],
        "baths_half": [1, 0],
        "year_built": [2005, 1998],
        "zip_code": ["78701", "78702"],
        "lat": [30.27, 30.28],
        "lng": [-97.74, -97.73],
        "sale_date": pd.to_datetime(["2022-01-15", "2022-04-10"]),
        "is_covid_period": [0, 0],
        "grade": ["B", "C"],
        "condition": ["GOOD", "AVERAGE"],
        "effective_year": [2010.0, 2005.0],
        "remodel_year": [2018.0, np.nan],
    })


def test_add_structural_grade_encoded():
    df = add_structural(_base_with_tcad())
    assert "grade_encoded" in df.columns
    assert df.loc[0, "grade_encoded"] == 4  # B -> 4
    assert df.loc[1, "grade_encoded"] == 3  # C -> 3


def test_add_structural_condition_encoded():
    df = add_structural(_base_with_tcad())
    assert "condition_encoded" in df.columns
    assert df.loc[0, "condition_encoded"] == 4  # GOOD -> 4
    assert df.loc[1, "condition_encoded"] == 3  # AVERAGE -> 3


def test_add_structural_years_since_remodel():
    df = add_structural(_base_with_tcad())
    assert "years_since_remodel" in df.columns
    assert df.loc[0, "years_since_remodel"] == 2024 - 2018  # 6
    # row 1: remodel_year NaN -> falls back to year_built 1998
    assert df.loc[1, "years_since_remodel"] == 2024 - 1998  # 26


def test_add_structural_defaults_when_no_tcad_cols():
    df_no_tcad = _base_with_tcad().drop(columns=["grade", "condition", "remodel_year", "effective_year"])
    df = add_structural(df_no_tcad)
    assert df["grade_encoded"].eq(0).all()
    assert df["condition_encoded"].eq(0).all()


def test_feature_cols_includes_tcad_features():
    for col in ["grade_encoded", "condition_encoded", "years_since_remodel"]:
        assert col in FEATURE_COLS


def test_build_feature_matrix_with_tcad_no_nulls():
    from avm.features import add_location, add_market_features, add_assessed_features
    df = _base_with_tcad()
    df["assessed_value"] = [420000.0, 360000.0]
    df = add_structural(df)
    df, _ = add_location(df)
    df = add_market_features(df)
    df = add_assessed_features(df)
    X = build_feature_matrix(df)
    assert X.isna().sum().sum() == 0
    assert "grade_encoded" in X.columns


def test_fetch_census_acs_income_uses_cache(tmp_path):
    cache = tmp_path / "zip_income.json"
    cache.write_text(json.dumps({"78701": 0.7, "78702": 0.5}))
    result = fetch_census_acs_income(["78701", "78702"], cache_path=cache)
    assert result["78701"] == pytest.approx(0.7)
    assert result["78702"] == pytest.approx(0.5)


def test_fetch_census_acs_income_falls_back_on_error(tmp_path):
    cache = tmp_path / "zip_income.json"
    with patch("requests.get", side_effect=OSError("no network")):
        result = fetch_census_acs_income(["78701", "78702"], cache_path=cache)
    assert result == {"78701": 0.5, "78702": 0.5}


def test_fetch_census_acs_income_normalises_to_0_1(tmp_path):
    cache = tmp_path / "zip_income.json"
    mock_data = [
        ["B19013_001E", "NAME", "zip code tabulation area"],
        ["50000", "ZCTA5 78701", "78701"],
        ["100000", "ZCTA5 78702", "78702"],
        ["75000", "ZCTA5 78703", "78703"],
    ]
    import requests
    mock_resp = type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: mock_data,
    })()
    with patch("requests.get", return_value=mock_resp):
        result = fetch_census_acs_income(["78701", "78702", "78703"], cache_path=cache)
    assert result["78701"] == pytest.approx(0.0)
    assert result["78702"] == pytest.approx(1.0)
    assert result["78703"] == pytest.approx(0.5)
```

---

## Task 8: Run Tests and Verify

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate/ml
source .venv/bin/activate
python -m pytest tests/ -v --tb=short 2>&1 | tee /tmp/avm_test_output.txt
```

Expected: all existing tests pass + all new tests in `test_ingest_tcad.py`, `test_clean_tcad.py`, `test_features_tcad.py` pass.

- [ ] **Step 2: Lint check**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate/ml
source .venv/bin/activate
python -m ruff check src/avm/ingest.py src/avm/clean.py src/avm/features.py run_training.py --fix
```

---

## Task 9: Retrain and Evaluate

- [ ] **Step 1: Smoke-run without TCAD (verify pipeline still works from Kaggle-only data)**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate/ml
source .venv/bin/activate
python run_training.py 5
```

Expected: completes without error, prints `TCAD data unavailable — proceeding without enrichment.`, MedAPE near 12.67%.

- [ ] **Step 2: Full retrain with TCAD (once TCAD CSV is in place)**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate/ml
source .venv/bin/activate
python run_training.py 50
```

Record MedAPE. Target: below 10%.

- [ ] **Step 3: Compare results**

```bash
python3 -c "
import json
from pathlib import Path
meta = json.loads(Path('models/meta.json').read_text())
baseline = 12.67
new = meta['test_medape']
print(f'Baseline MedAPE: {baseline:.2f}%')
print(f'New MedAPE:      {new:.2f}%')
print(f'Delta:           {new - baseline:+.2f}% ({(new-baseline)/baseline*100:+.1f}%)')
print(f'Version:         {meta[\"version\"]}')
print(f'TCAD enriched:   {meta.get(\"tcad_enriched\", False)}')
"
```

---

## Task 10: Push Artifacts to HuggingFace (if improved)

Run this only if new MedAPE < 12.67%.

- [ ] **Step 1: Push model artifacts**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate
source ml/.venv/bin/activate
python3 -c "
from huggingface_hub import HfApi
import os
api = HfApi()
# Replace with your HF repo ID
repo_id = 'Ofunrein/austin-avm'
for f in ['ml/models/xgb_model.joblib', 'ml/models/lgb_model.joblib',
          'ml/models/meta.json', 'ml/models/q_low.joblib', 'ml/models/q_high.joblib']:
    from pathlib import Path
    if Path(f).exists():
        api.upload_file(path_or_fileobj=f, path_in_repo=Path(f).name, repo_id=repo_id)
        print(f'Uploaded {f}')
"
```

---

## Dependency Summary

New packages required:

| Package | Version | Purpose |
|---|---|---|
| `rapidfuzz` | >=3.6 | Fuzzy address matching in `merge_tcad` |

Add to `ml/pyproject.toml`:
```toml
"rapidfuzz>=3.6",
```

Install:
```bash
cd /Users/martinofunrein/Downloads/avm-zestimate/ml
source .venv/bin/activate
uv pip install "rapidfuzz>=3.6"
```

---

## Risk Notes

- TCAD download URL is not stable. If the page structure changes, `fetch_tcad` returns `None` and training proceeds on Kaggle-only data. No breakage.
- TCAD address format varies by year. The `_find_tcad_csv` heuristic (filename candidates + size threshold) covers all known formats from 2019-2024 exports.
- Fuzzy match `score_cutoff=88` was chosen to balance precision (avoid wrong-property merges) vs recall. If match rate is below 40%, lower to 82 and re-evaluate.
- Census ACS API is rate-limited to ~500 req/day anonymously. The full ZCTA query (single request) is well within limits.
- If `effective_year` is unavailable in TCAD (some years omit it), `effective_age` in `add_structural` already falls back to `year_built` via the existing `features.py` logic.
