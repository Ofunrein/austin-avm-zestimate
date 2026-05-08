from fastapi import APIRouter
import json
from pathlib import Path
from api.schemas import BenchmarkResponse

router = APIRouter()


@router.get("/benchmark", response_model=BenchmarkResponse)
def get_benchmark():
    meta_path = Path(__file__).parents[3] / "ml/models/meta.json"
    residuals_path = Path(__file__).parents[3] / "ml/models/residuals.json"

    if not meta_path.exists():
        return BenchmarkResponse(
            model_version="not-trained",
            test_medape=0, test_mae=0, test_rmse=0,
            test_within_5pct=0, test_within_10pct=0, n_test=0,
            baseline_zip_median_medape=0, baseline_ppsf_medape=0,
            by_zip=[],
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
