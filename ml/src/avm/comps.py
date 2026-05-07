"""Find comparable sold properties using feature similarity."""
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


COMP_FEATURES = ["sqft_living", "beds", "bath_total", "age", "lot_sqft"]
EARTH_RADIUS_MILES = 3958.8


def haversine_miles(lat1, lng1, lat2_arr, lng2_arr) -> np.ndarray:
    """Vectorised haversine distance in miles."""
    R = EARTH_RADIUS_MILES
    lat1, lng1 = np.radians(lat1), np.radians(lng1)
    lat2 = np.radians(lat2_arr)
    lng2 = np.radians(lng2_arr)
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def find_comps(
    subject: dict,
    sold_df: pd.DataFrame,
    n: int = 5,
    radius_miles: float = 1.0,
    sqft_tolerance: float = 0.20,
    age_tolerance: int = 5,
) -> pd.DataFrame:
    """
    subject keys: lat, lng, sqft_living, beds, bath_total, age
    Returns top n comparable sales sorted by cosine similarity.
    """
    df = sold_df.copy()

    # geographic filter
    dists = haversine_miles(
        subject["lat"], subject["lng"],
        df["lat"].values, df["lng"].values,
    )
    df["_dist"] = dists
    df = df[dists <= radius_miles]
    if df.empty:
        df = sold_df.copy()  # fallback: drop radius filter
        df["_dist"] = haversine_miles(
            subject["lat"], subject["lng"],
            df["lat"].values, df["lng"].values,
        )

    # sqft filter ±20%
    sqft = subject["sqft_living"]
    df = df[df["sqft_living"].between(sqft * (1 - sqft_tolerance), sqft * (1 + sqft_tolerance))]

    # age filter ±5 years
    age = subject.get("age", 20)
    age_col = df["age"] if "age" in df.columns else pd.Series([age] * len(df), index=df.index)
    df = df[age_col.between(age - age_tolerance, age + age_tolerance)]

    if df.empty:
        return pd.DataFrame()

    # cosine similarity on normalised features
    features = [f for f in COMP_FEATURES if f in df.columns]
    subj_vec = np.array([[subject.get(f, 0) for f in features]])
    all_vecs = df[features].fillna(0).values

    all_norm = np.linalg.norm(all_vecs, axis=1, keepdims=True).clip(1e-9)
    subj_norm = np.linalg.norm(subj_vec).clip(1e-9)
    similarities = (all_vecs / all_norm) @ (subj_vec / subj_norm).T
    df["similarity_score"] = similarities.flatten().clip(0, 1)

    top = df.nlargest(n, "similarity_score")
    return_cols = [c for c in ["address", "sale_price", "sale_date", "sqft_living",
                               "beds", "bath_total", "zip_code", "_dist", "similarity_score"]
                  if c in top.columns]
    return top[return_cols].rename(columns={"_dist": "distance_miles"}).reset_index(drop=True)
