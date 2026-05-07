"""Download and parse all raw data sources into standardized DataFrames."""
import os
import subprocess
import zipfile
from pathlib import Path

import pandas as pd
from numbers_parser import Document

RAW = Path(__file__).parents[3] / "data/raw"
PROCESSED = Path(__file__).parents[3] / "data/processed"

KAGGLE_DATASET = "ericpierce/austinhousingprices"
NUMBERS_PATH = Path.home() / "Downloads/compass_austin_listings.numbers"


def fetch_kaggle_austin(dest: Path = RAW) -> Path:
    """Download Austin housing prices dataset from Kaggle."""
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "kaggle_austin"
    if (out / "austinHousingData.csv").exists():
        return out / "austinHousingData.csv"
    subprocess.run(
        ["kaggle", "datasets", "download", "-d", KAGGLE_DATASET, "-p", str(out), "--unzip"],
        check=True,
    )
    csvs = list(out.glob("*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No CSV found after Kaggle download in {out}")
    return csvs[0]


def parse_numbers_listings(path: Path = NUMBERS_PATH) -> pd.DataFrame:
    """Parse Apple .numbers file into DataFrame."""
    if not path.exists():
        raise FileNotFoundError(f"Numbers file not found: {path}")
    doc = Document(str(path))
    sheet = doc.sheets[0]
    table = sheet.tables[0]
    rows = [[cell.value for cell in row] for row in table.iter_rows()]
    if not rows:
        return pd.DataFrame()
    headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
    return pd.DataFrame(rows[1:], columns=headers)


def load_kaggle_austin(path: Path | None = None) -> pd.DataFrame:
    """Load Kaggle Austin CSV into standardized DataFrame."""
    if path is None:
        path = fetch_kaggle_austin()
    df = pd.read_csv(path, low_memory=False)
    return df


def load_compass_listings() -> pd.DataFrame:
    return parse_numbers_listings()


def save_raw(df: pd.DataFrame, name: str) -> Path:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / f"{name}.parquet"
    df.to_parquet(out, index=False)
    return out
