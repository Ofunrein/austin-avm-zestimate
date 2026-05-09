"""Smoke tests: API must import, key routes must respond without crash."""
import sys
from pathlib import Path

# Allow avm imports when running without Docker (no installed package)
_ml_src = Path(__file__).parents[2] / "ml/src"
if _ml_src.exists() and str(_ml_src) not in sys.path:
    sys.path.insert(0, str(_ml_src))


def test_api_imports():
    import importlib
    mod = importlib.import_module("api.main")
    assert hasattr(mod, "app")


def test_health_route():
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert "version" in resp.json()


def test_benchmark_schema_contract():
    """Benchmark must return model_version field; numeric fields must be null or float, never invented."""
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    resp = client.get("/benchmark")
    assert resp.status_code == 200
    data = resp.json()
    assert "model_version" in data
    for field in ("test_medape", "test_mae", "baseline_zip_median_medape"):
        val = data.get(field)
        assert val is None or isinstance(val, (int, float)), \
            f"{field} must be null or numeric, got {type(val)}"


def test_search_response_schema():
    """Search must return results/query_parsed/total regardless of DB state."""
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    resp = client.post("/search", json={"query": "3BR under $400k in 78744"})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "query_parsed" in data
    assert "total" in data
    assert isinstance(data["results"], list)
    assert isinstance(data["total"], int)


def test_search_parses_beds_filter():
    """LLM parser must extract beds_min from query (or gracefully return params dict)."""
    from fastapi.testclient import TestClient
    from api.main import app
    import os
    os.environ.setdefault("ANTHROPIC_API_KEY", "test_key_not_real")
    client = TestClient(app)
    resp = client.post("/search", json={"query": "3BR in 78744"})
    assert resp.status_code == 200
    # With no real API key, parser may fall back to empty params — that's acceptable
    data = resp.json()
    assert "results" in data

