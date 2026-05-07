"""Feature engineering for Austin AVM."""
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

# Austin downtown coords
DOWNTOWN_LAT = 30.2672
DOWNTOWN_LNG = -97.7431


def add_structural(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["age"] = 2024 - df["year_built"].clip(1850, 2024)
    eff_year = df["effective_year"] if "effective_year" in df.columns else df["year_built"]
    df["effective_age"] = (2024 - eff_year).clip(0, 174)
    df["has_pool"] = (df["has_pool"] if "has_pool" in df.columns else pd.Series(0, index=df.index)).fillna(0).astype(int)
    garage = df["garage_spaces"] if "garage_spaces" in df.columns else pd.Series(0, index=df.index)
    garage = garage.fillna(0)
    df["has_garage"] = (garage > 0).astype(int)
    df["garage_spaces"] = garage.clip(0, 10)
    df["baths_half"] = (df["baths_half"] if "baths_half" in df.columns else pd.Series(0, index=df.index)).fillna(0)
    df["bath_total"] = df["baths_full"] + 0.5 * df["baths_half"]
    df["sqft_per_bed"] = (df["sqft_living"] / df["beds"].replace(0, 1)).clip(0, 5000)
    lot = df["lot_sqft"] if "lot_sqft" in df.columns else pd.Series(0, index=df.index)
    df["lot_sqft"] = lot.fillna(0).clip(0, 500_000)
    df["lot_to_living_ratio"] = (df["lot_sqft"] / df["sqft_living"].replace(0, 1)).clip(0, 100)
    return df


def add_location(df: pd.DataFrame, income_lookup: dict | None = None) -> pd.DataFrame:
    df = df.copy()
    # Euclidean proxy for distance (fast, good enough for Austin's flat terrain)
    lat_diff = df["lat"] - DOWNTOWN_LAT
    lng_diff = df["lng"] - DOWNTOWN_LNG
    df["dist_downtown_miles"] = np.sqrt(lat_diff**2 + lng_diff**2) * 69.0

    # ZIP income score (0–1). Pass in dict {zip: normalised_income} from Census ACS.
    if income_lookup:
        df["zip_income_score"] = df["zip_code"].map(income_lookup).fillna(0.5)
    else:
        df["zip_income_score"] = 0.5  # neutral default

    # Label-encode zip for tree models
    le = LabelEncoder()
    df["zip_encoded"] = le.fit_transform(df["zip_code"].astype(str))
    return df, le


def add_market_features(df: pd.DataFrame) -> pd.DataFrame:
    """Rolling 90-day ZIP medians — computed without future leakage."""
    df = df.copy()
    if "sale_date" not in df.columns:
        df["median_zip_price_90d"] = df.get("sale_price", 400_000)
        df["median_zip_ppsf_90d"] = 250.0
        return df

    df = df.sort_values("sale_date").reset_index(drop=True)
    df["ppsf"] = df["sale_price"] / df["sqft_living"].replace(0, 1)

    results = []
    for zip_code, grp in df.groupby("zip_code"):
        grp = grp.sort_values("sale_date").copy()
        # Use expanding shifted median to avoid same-row leakage
        # For each row i, median of all rows j < i within 90 days before sale_date[i]
        prices = grp["sale_price"].values
        dates = grp["sale_date"].values
        ppsfs = grp["ppsf"].values
        n = len(grp)
        med_prices = np.full(n, np.nan)
        med_ppsfs = np.full(n, np.nan)
        cutoff_90d = np.timedelta64(90, "D")
        for i in range(n):
            # include only rows strictly before index i
            if i == 0:
                continue
            mask = dates[:i] >= (dates[i] - cutoff_90d)
            window_prices = prices[:i][mask]
            window_ppsfs = ppsfs[:i][mask]
            if len(window_prices) > 0:
                med_prices[i] = np.median(window_prices)
                med_ppsfs[i] = np.median(window_ppsfs)
        grp = grp.copy()
        grp["median_zip_price_90d"] = med_prices
        grp["median_zip_ppsf_90d"] = med_ppsfs
        results.append(grp)

    out = pd.concat(results).sort_index()
    # fill NaN (first rows in each zip) with global median
    out["median_zip_price_90d"] = out["median_zip_price_90d"].fillna(out["sale_price"].median())
    out["median_zip_ppsf_90d"] = out["median_zip_ppsf_90d"].fillna(out["ppsf"].median())
    out = out.drop(columns=["ppsf"], errors="ignore")
    return out


def add_assessed_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "assessed_value" in df.columns:
        df["price_per_sqft_assessed"] = (
            df["assessed_value"] / df["sqft_living"].replace(0, 1)
        ).clip(0, 2000)
        df["assessed_ratio"] = (df["assessed_value"] / df["sale_price"].replace(0, 1)).clip(0, 5)
    else:
        df["price_per_sqft_assessed"] = 0.0
        df["assessed_ratio"] = 0.0
    return df


FEATURE_COLS = [
    "sqft_living", "lot_sqft", "beds", "baths_full", "baths_half", "bath_total",
    "year_built", "age", "effective_age", "stories",
    "has_pool", "has_garage", "garage_spaces",
    "sqft_per_bed", "lot_to_living_ratio",
    "dist_downtown_miles", "zip_income_score", "zip_encoded",
    "median_zip_price_90d", "median_zip_ppsf_90d",
    "price_per_sqft_assessed", "assessed_ratio",
    "is_covid_period",
]


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Return only model feature columns, filling missing with 0."""
    cols = [c for c in FEATURE_COLS if c in df.columns]
    return df[cols].fillna(0).astype(float)
