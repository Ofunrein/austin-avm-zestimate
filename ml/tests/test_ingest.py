import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from avm.ingest import load_kaggle_austin, parse_numbers_listings, save_raw


def test_load_kaggle_returns_dataframe(tmp_path):
    csv = tmp_path / "austin.csv"
    csv.write_text("zpid,latestPrice,livingAreaSqFt,numOfBedrooms,numOfBathrooms,yearBuilt,zipcode\n"
                   "1,450000,1800,3,2,2005,78701\n")
    df = load_kaggle_austin(path=csv)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "latestPrice" in df.columns


def test_save_raw_writes_parquet(tmp_path):
    import avm.ingest as ingest_module
    ingest_module.PROCESSED = tmp_path
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    out = save_raw(df, "test")
    assert out.exists()
    loaded = pd.read_parquet(out)
    assert len(loaded) == 2
