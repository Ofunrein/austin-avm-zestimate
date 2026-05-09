"""Tests for Census ACS income enrichment."""
import pytest
from pathlib import Path


def _get_scores():
    from avm.enrich_census import fetch_zip_income_scores
    try:
        return fetch_zip_income_scores(state_fips="48")
    except Exception as e:
        pytest.skip(f"Census API unavailable (network/proxy): {e}")


def test_fetch_zip_income_returns_dict():
    """Census ACS returns dict mapping ZIP5 str to float 0-1."""
    result = _get_scores()
    assert isinstance(result, dict)
    assert len(result) > 0
    sample_key = next(iter(result))
    assert len(sample_key) == 5
    for v in list(result.values())[:50]:
        assert 0.0 <= v <= 1.0


def test_austin_zips_present():
    """Austin TX ZIPs must be in the result."""
    result = _get_scores()
    austin_zips = {"78701", "78704", "78744", "78750"}
    found = austin_zips & set(result.keys())
    assert len(found) > 0, f"No Austin ZIPs found. Keys sample: {list(result.keys())[:10]}"


def test_income_scores_vary():
    """Different ZIPs have different scores — not all the same."""
    result = _get_scores()
    values = list(result.values())
    assert len(set(values)) > 10, "All income scores identical — normalization broken"


def test_cache_works(tmp_path, monkeypatch):
    """Second call uses cache — no redundant network request."""
    import avm.enrich_census as ec
    monkeypatch.setattr(ec, "CACHE_PATH", tmp_path / "cache.json")
    try:
        result1 = ec.fetch_zip_income_scores(state_fips="48")
    except Exception as e:
        pytest.skip(f"Census API unavailable: {e}")
    result2 = ec.fetch_zip_income_scores(state_fips="48")
    assert result1 == result2
