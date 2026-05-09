from fastapi import APIRouter
import json
from pathlib import Path
from api.schemas import BenchmarkResponse

router = APIRouter()


@router.get("/benchmark", response_model=BenchmarkResponse)
def get_benchmark():
    meta_path = Path(__file__).parents[2] / "ml/models/meta.json"
    residuals_path = Path(__file__).parents[2] / "ml/models/residuals.json"

    if not meta_path.exists():
        return BenchmarkResponse(model_version="not-trained")

    meta = json.loads(meta_path.read_text())
    residuals = json.loads(residuals_path.read_text()) if residuals_path.exists() else {}
    overall = residuals.get("overall", {})

    return BenchmarkResponse(
        model_version=meta.get("version", "1.0.0"),
        test_medape=meta.get("test_medape") or None,
        test_mae=overall.get("mae") or None,
        test_rmse=overall.get("rmse") or None,
        test_within_5pct=overall.get("within_5pct") or None,
        test_within_10pct=overall.get("within_10pct") or None,
        n_test=overall.get("n") or None,
        baseline_zip_median_medape=meta.get("test_medape_zip_median") or None,
        baseline_ppsf_medape=meta.get("test_medape_ppsf") or None,
        by_zip=residuals.get("by_zip", []),
    )
