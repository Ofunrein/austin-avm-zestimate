from fastapi import APIRouter
from api.schemas import ExplainRequest, ExplainResponse
from api.services.llm import explain_prediction

router = APIRouter()


@router.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest):
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
        neighborhood_context=req.neighborhood_context,
    )
    return ExplainResponse(explanation=text)
