"""Merge, deduplicate, and clean Austin sale records."""
import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd


# ── Column normalisation maps ──────────────────────────────────────────────

KAGGLE_RENAME = {
    "latestPrice": "sale_price",
    "livingAreaSqFt": "sqft_living",
    "lotSizeSqFt": "lot_sqft",
    "numOfBedrooms": "beds",
    "numOfBathrooms": "baths_full",
    "yearBuilt": "year_built",
    "zipcode": "zip_code",
    "latitude": "lat",
    "longitude": "lng",
    "garageSpaces": "garage_spaces",
    "hasAssociation": "has_hoa",
    "hasSpa": "has_spa",
    "hasView": "has_view",
    "latest_saledate": "sale_date",
    "city": "city",
    "homeType": "property_type",
    "numOfStories": "stories",
    "avgSchoolRating": "school_rating",
    "MedianStudentsPerTeacher": "students_per_teacher",
    "numOfHighSchools": "n_high_schools",
    "numOfMiddleSchools": "n_middle_schools",
    "numOfElementarySchools": "n_elem_schools",
}

REQUIRED_COLS = [
    "sale_price", "sqft_living", "beds", "baths_full",
    "year_built", "zip_code", "lat", "lng",
]


def normalise_kaggle(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={k: v for k, v in KAGGLE_RENAME.items() if k in df.columns})
    if "sale_date" not in df.columns:
        for c in ["latestSaleDate", "lastsolddate", "latest_saledate"]:
            if c in df.columns:
                df["sale_date"] = pd.to_datetime(df[c], errors="coerce")
                break
    else:
        df["sale_date"] = pd.to_datetime(df["sale_date"], errors="coerce")
    df["source"] = "kaggle"
    return df


def _normalise_address(addr: str) -> str:
    if not isinstance(addr, str):
        return ""
    addr = addr.upper().strip()
    addr = re.sub(r"\s+", " ", addr)
    for old, new in [(" STREET", " ST"), (" AVENUE", " AVE"), (" DRIVE", " DR"),
                     (" ROAD", " RD"), (" LANE", " LN"), (" COURT", " CT"),
                     (" BOULEVARD", " BLVD"), (" PLACE", " PL")]:
        addr = addr.replace(old, new)
    return addr


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # drop missing required fields
    df = df.dropna(subset=[c for c in REQUIRED_COLS if c in df.columns])

    # price sanity: Austin homes $50k–$10M
    df = df[df["sale_price"].between(50_000, 10_000_000)]

    # sqft sanity: 200–20,000
    df = df[df["sqft_living"].between(200, 20_000)]

    # beds/baths
    df = df[df["beds"].between(0, 20)]
    df = df[df["baths_full"].between(0, 20)]

    # year built sanity
    df = df[df["year_built"].between(1850, 2025)]

    # normalise zip to 5-digit string
    df["zip_code"] = df["zip_code"].astype(str).str[:5].str.zfill(5)

    # filter to Travis County ZIPs (Austin area: 786xx + 787xx)
    df = df[df["zip_code"].str.match(r"^78[67]\d{2}$")]

    # COVID flag
    if "sale_date" in df.columns:
        df["sale_date"] = pd.to_datetime(df["sale_date"], errors="coerce")
        covid_start = pd.Timestamp("2020-04-01")
        covid_end = pd.Timestamp("2021-06-30")
        df["is_covid_period"] = df["sale_date"].between(covid_start, covid_end).astype(int)
        df = df[df["sale_date"].between("2018-01-01", "2024-12-31")]
    else:
        df["is_covid_period"] = 0

    # dedup on address + sale_date
    if "address" in df.columns and "sale_date" in df.columns:
        df["_addr_norm"] = df["address"].apply(_normalise_address)
        df = df.drop_duplicates(subset=["_addr_norm", "sale_date"])
        df = df.drop(columns=["_addr_norm"])

    df = df.reset_index(drop=True)
    return df


def data_sha256(df: pd.DataFrame) -> str:
    """Reproducible hash of dataset for MLflow."""
    h = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes())
    return h.hexdigest()[:16]
