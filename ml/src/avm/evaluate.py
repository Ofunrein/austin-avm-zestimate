"""Model evaluation: metrics + residual analysis."""
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    ape = np.abs(y_true - y_pred) / np.abs(y_true) * 100
    return {
        "medape": float(np.median(ape)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "within_5pct": float(np.mean(ape <= 5)),
        "within_10pct": float(np.mean(ape <= 10)),
        "n": int(len(y_true)),
    }


def metrics_by_zip(df: pd.DataFrame, y_pred: np.ndarray) -> pd.DataFrame:
    df = df.copy()
    df["y_pred"] = y_pred
    rows = []
    for zip_code, grp in df.groupby("zip_code"):
        m = metrics(grp["sale_price"].values, grp["y_pred"].values)
        m["zip_code"] = zip_code
        m["n_sales"] = len(grp)
        rows.append(m)
    return pd.DataFrame(rows).sort_values("medape")


def metrics_by_price_tier(df: pd.DataFrame, y_pred: np.ndarray) -> pd.DataFrame:
    df = df.copy()
    df["y_pred"] = y_pred
    df["price_tier"] = pd.cut(
        df["sale_price"],
        bins=[0, 300_000, 500_000, 750_000, 1_000_000, 99_000_000],
        labels=["<300k", "300-500k", "500-750k", "750k-1M", ">1M"],
    )
    rows = []
    for tier, grp in df.groupby("price_tier", observed=True):
        if len(grp) < 5:
            continue
        m = metrics(grp["sale_price"].values, grp["y_pred"].values)
        m["price_tier"] = str(tier)
        rows.append(m)
    return pd.DataFrame(rows)


def metrics_by_year_built(df: pd.DataFrame, y_pred: np.ndarray) -> pd.DataFrame:
    df = df.copy()
    df["y_pred"] = y_pred
    df["era"] = pd.cut(
        df["year_built"],
        bins=[0, 1970, 1990, 2005, 2015, 2100],
        labels=["pre-1970", "1970-1990", "1990-2005", "2005-2015", "post-2015"],
    )
    rows = []
    for era, grp in df.groupby("era", observed=True):
        if len(grp) < 5:
            continue
        m = metrics(grp["sale_price"].values, grp["y_pred"].values)
        m["era"] = str(era)
        rows.append(m)
    return pd.DataFrame(rows)


def residual_summary(df: pd.DataFrame, y_pred: np.ndarray) -> dict:
    return {
        "overall": metrics(df["sale_price"].values, y_pred),
        "by_zip": metrics_by_zip(df, y_pred).to_dict(orient="records"),
        "by_price_tier": metrics_by_price_tier(df, y_pred).to_dict(orient="records"),
        "by_year_built": metrics_by_year_built(df, y_pred).to_dict(orient="records"),
    }
