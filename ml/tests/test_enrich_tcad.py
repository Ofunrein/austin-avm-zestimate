"""Tests for TCAD parcel data enrichment."""
import io
import pytest
import pandas as pd
from pathlib import Path

TCAD_CSV = Path(__file__).parents[1] / "data/raw/tcad_parcels.csv"


def _make_csv(rows: list[dict]) -> str:
    import csv, io
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def test_build_tcad_lookup_empty_dict_if_missing(tmp_path):
    """Returns empty dict when CSV not found — no crash."""
    from avm.enrich_tcad import build_tcad_lookup
    result = build_tcad_lookup(tmp_path / "nonexistent.csv")
    assert result == {}


def test_build_tcad_lookup_parses_correctly(tmp_path):
    """Parses standard TCAD column names correctly."""
    from avm.enrich_tcad import build_tcad_lookup
    csv_content = _make_csv([
        {"situs_address": "1234 Main St", "appraised_value": "350000"},
        {"situs_address": "5678 Oak Ave, Austin TX", "appraised_value": "425,000"},
        {"situs_address": "999 Bad St", "appraised_value": "-1"},  # should be skipped
    ])
    p = tmp_path / "test.csv"
    p.write_text(csv_content)
    result = build_tcad_lookup(p)
    assert "1234 main st" in result
    assert result["1234 main st"] == 350000.0
    assert "5678 oak ave" in result
    assert result["5678 oak ave"] == 425000.0
    assert len([k for k, v in result.items() if v < 0]) == 0


def test_build_tcad_lookup_handles_alternate_columns(tmp_path):
    """Handles alternate TCAD column name formats."""
    from avm.enrich_tcad import build_tcad_lookup
    csv_content = _make_csv([
        {"SitusAddress": "100 Test Blvd", "TotApprVal": "500000"},
    ])
    p = tmp_path / "alt.csv"
    p.write_text(csv_content)
    result = build_tcad_lookup(p)
    assert len(result) == 1


def test_lookup_appraised_value():
    """Address normalization finds match despite case/punctuation."""
    from avm.enrich_tcad import lookup_appraised_value
    tcad = {"1234 main st": 350000.0, "5678 oak ave": 425000.0}
    assert lookup_appraised_value("1234 Main St, Austin TX", tcad) == 350000.0
    assert lookup_appraised_value("5678 OAK AVE", tcad) == 425000.0
    assert lookup_appraised_value("9999 Unknown Rd", tcad) is None


def test_real_tcad_csv_if_available():
    """Integration test — runs only if TCAD CSV is downloaded."""
    if not TCAD_CSV.exists():
        pytest.skip("TCAD CSV not downloaded — run from traviscad.org")
    from avm.enrich_tcad import build_tcad_lookup
    result = build_tcad_lookup(TCAD_CSV)
    assert len(result) > 1000, f"Expected 1000+ parcels, got {len(result)}"
    sample_values = list(result.values())[:100]
    assert all(v > 0 for v in sample_values)
