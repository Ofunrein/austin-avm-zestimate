from fastapi import APIRouter
import json
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from api.schemas import BenchmarkResponse
from api.db import db

router = APIRouter()
_CACHE_TTL_HOURS = 24


def _read_from_files() -> BenchmarkResponse:
    meta_path = Path(__file__).parents[2] / "ml/models/meta.json"
    residuals_path = Path(__file__).parents[2] / "ml/models/residuals.json"
    if not meta_path.exists():
        return BenchmarkResponse(
            model_version="not-trained", test_medape=0, test_mae=0, test_rmse=0,
            test_within_5pct=0, test_within_10pct=0, n_test=0,
            baseline_zip_median_medape=0, baseline_ppsf_medape=0, by_zip=[],
        )
    meta = json.loads(meta_path.read_text())
    residuals = json.loads(residuals_path.read_text()) if residuals_path.exists() else {}
    overall = residuals.get("overall", {})
    return BenchmarkResponse(
        model_version=meta.get("version", "1.0.0"),
        test_medape=meta.get("test_medape", 0),
        test_mae=overall.get("mae", 0),
        test_rmse=overall.get("rmse", 0),
        test_within_5pct=overall.get("within_5pct", 0),
        test_within_10pct=overall.get("within_10pct", 0),
        n_test=overall.get("n", 0),
        baseline_zip_median_medape=0,
        baseline_ppsf_medape=0,
        by_zip=residuals.get("by_zip", []),
    )


def _row_to_response(row: dict) -> BenchmarkResponse:
    return BenchmarkResponse(
        model_version=row["model_version"],
        test_medape=row.get("medape", 0),
        test_mae=row.get("mae", 0),
        test_rmse=row.get("rmse", 0),
        test_within_5pct=row.get("within_5pct", 0),
        test_within_10pct=row.get("within_10pct", 0),
        n_test=row.get("n_test", 0),
        baseline_zip_median_medape=0,
        baseline_ppsf_medape=0,
        by_zip=row.get("residuals_json", {}).get("by_zip", []) if row.get("residuals_json") else [],
    )


@router.get("/benchmark", response_model=BenchmarkResponse)
def get_benchmark():
    if db is not None:
        try:
            result = db.table("benchmark_runs").select("*").order("created_at", desc=True).limit(1).execute()
            rows = result.data
            if rows:
                row = rows[0]
                created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - created_at < timedelta(hours=_CACHE_TTL_HOURS):
                    return _row_to_response(row)
        except Exception:
            traceback.print_exc()

    fresh = _read_from_files()

    if db is not None:
        try:
            residuals_path = Path(__file__).parents[2] / "ml/models/residuals.json"
            residuals_raw = json.loads(residuals_path.read_text()) if residuals_path.exists() else {}
            db.table("benchmark_runs").insert({
                "model_version": fresh.model_version,
                "medape": fresh.test_medape, "mae": fresh.test_mae,
                "rmse": fresh.test_rmse, "within_5pct": fresh.test_within_5pct,
                "within_10pct": fresh.test_within_10pct, "n_test": fresh.n_test,
                "test_period": None, "residuals_json": residuals_raw,
            }).execute()
        except Exception:
            traceback.print_exc()

    return fresh
