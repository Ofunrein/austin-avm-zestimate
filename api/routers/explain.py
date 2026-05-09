from fastapi import APIRouter
from api.schemas import ExplainRequest, ExplainResponse
from api.services.llm import explain_prediction
from api.services.neighborhood import fetch_neighborhood

router = APIRouter()


@router.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest):
    ctx = req.neighborhood_context
    if not ctx and req.zip_code:
        try:
            data = fetch_neighborhood(req.zip_code)
            parts = []
            if data.get("walk_score"):
                parts.append(f"Walk Score {data['walk_score']}")
            if data.get("school_rating"):
                parts.append(f"schools {data['school_rating']}/10")
            if data.get("median_income"):
                parts.append(f"median income ${data['median_income']:,}")
            ctx = ", ".join(parts) if parts else ""
        except Exception:
            ctx = ""

    text = explain_prediction(
        predicted_price=req.predicted_price,
        lower_bound=req.lower_bound,
        upper_bound=req.upper_bound,
        confidence_score=req.confidence_score,
        shap_top5=[f.model_dump() for f in req.shap_top5],
        zip_code=req.zip_code,
        sqft=req.sqft_living,
        beds=req.beds,
        baths=req.baths_full,
        year_built=req.year_built,
        neighborhood_context=ctx,
    )
    return ExplainResponse(explanation=text)
