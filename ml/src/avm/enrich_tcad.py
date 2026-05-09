"""
TCAD (Travis County Appraisal District) parcel data enrichment.

Download the bulk CSV from https://traviscad.org/appraisaldata
("Export Property Data" — free, no login required).
Save to ml/data/raw/tcad_parcels.csv.

Column names vary by year. This module handles the most common TCAD export formats.

Usage:
    from avm.enrich_tcad import build_tcad_lookup, lookup_appraised_value
    tcad = build_tcad_lookup(Path("ml/data/raw/tcad_parcels.csv"))
    value = lookup_appraised_value("3525 lost creek blvd", tcad)
"""
import re
from pathlib import Path
import pandas as pd

# TCAD export column name variants across years
_APPRAISED_COLS = [
    "appraised_value", "AppraisedValue", "APPRAISED_VALUE",
    "tot_appr_val", "TotApprVal", "total_appraised_value",
    "totalAppraisedValue", "appr_val",
]
_ADDRESS_COLS = [
    "address", "situs_address", "SitusAddress", "SITUS_ADDRESS",
    "situs_addr", "SitusAddr", "property_address",
    "PropertyAddress", "PROPERTY_ADDRESS", "addr",
]


def _normalize_address(addr: str) -> str:
    """Lowercase, strip unit/apartment numbers, collapse whitespace."""
    addr = str(addr).lower().strip()
    # Remove city/state/zip suffix (everything after comma)
    addr = addr.split(",")[0].strip()
    # Remove unit designators
    addr = re.sub(r"\b(apt|unit|#|ste|suite|fl|floor)\s*\S+", "", addr)
    # Normalize direction abbreviations
    addr = re.sub(r"\be\b", "east", addr)
    addr = re.sub(r"\bw\b", "west", addr)
    addr = re.sub(r"\bn\b", "north", addr)
    addr = re.sub(r"\bs\b", "south", addr)
    return re.sub(r"\s+", " ", addr).strip()


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    lower_map = {col.lower(): col for col in df.columns}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def build_tcad_lookup(csv_path: Path) -> dict[str, float]:
    """Parse TCAD bulk CSV → dict mapping normalized address to appraised value.

    Returns empty dict if CSV not found (fail-soft for training pipeline).
    """
    if not csv_path.exists():
        return {}

    df = pd.read_csv(csv_path, low_memory=False, dtype=str)

    addr_col = _find_col(df, _ADDRESS_COLS)
    appr_col = _find_col(df, _APPRAISED_COLS)

    if not addr_col or not appr_col:
        raise ValueError(
            f"Cannot find address/appraised columns in TCAD CSV.\n"
            f"Expected one of: {_ADDRESS_COLS}\n"
            f"Expected one of: {_APPRAISED_COLS}\n"
            f"Found columns: {list(df.columns[:30])}"
        )

    lookup: dict[str, float] = {}
    for _, row in df[[addr_col, appr_col]].iterrows():
        try:
            raw_val = str(row[appr_col]).replace(",", "").replace("$", "").strip()
            value = float(raw_val)
            if value <= 0:
                continue
            key = _normalize_address(row[addr_col])
            if key and len(key) > 3:
                lookup[key] = value
        except (ValueError, TypeError):
            continue

    return lookup


def lookup_appraised_value(address: str, tcad: dict[str, float]) -> float | None:
    """Look up appraised value for an address string. Returns None if not found."""
    key = _normalize_address(address)
    return tcad.get(key)
