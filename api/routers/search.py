from fastapi import APIRouter
from api.schemas import SearchRequest, SearchResponse, SearchResult
from api.services.llm import parse_search_query
from api.services.neighborhood import fetch_neighborhood
from api.db import db

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    try:
        params = parse_search_query(req.query)
    except Exception:
        params = {"undervalued_only": False}

    if not db:
        return SearchResponse(results=[], query_parsed=params, total=0)

    q = db.table("predictions").select(
        "id,address,zip_code,sqft_living,beds,baths_full,year_built,"
        "predicted_price,list_price,confidence_score,shap_json,created_at"
    )

    if params.get("beds_min"):
        q = q.gte("beds", params["beds_min"])
    if params.get("baths_min"):
        q = q.gte("baths_full", params["baths_min"])
    if params.get("sqft_min"):
        q = q.gte("sqft_living", params["sqft_min"])
    if params.get("sqft_max"):
        q = q.lte("sqft_living", params["sqft_max"])
    if params.get("price_max"):
        q = q.lte("predicted_price", params["price_max"])
    if params.get("zip_codes"):
        q = q.in_("zip_code", params["zip_codes"])
    if params.get("year_built_min"):
        q = q.gte("year_built", params["year_built_min"])

    # undervalued_only: value_gap_pct is not a DB column — filter in Python after fetch
    if params.get("undervalued_only"):
        q = q.not_.is_("list_price", "null").order("predicted_price", desc=True)
    else:
        q = q.order("predicted_price", desc=True)

    rows = q.limit(50).execute().data

    results: list[SearchResult] = []
    for r in rows:
        shap_json = r.get("shap_json") or []
        top_driver = shap_json[0]["feature"] if shap_json else None
        list_price = r.get("list_price")
        gap = (
            round((r["predicted_price"] - list_price) / list_price * 100, 1)
            if list_price and list_price > 0
            else None
        )
        results.append(SearchResult(
            id=str(r["id"]),
            address=r.get("address"),
            zip_code=r.get("zip_code"),
            sqft_living=r.get("sqft_living"),
            beds=r.get("beds"),
            baths_full=r.get("baths_full"),
            year_built=r.get("year_built"),
            predicted_price=r["predicted_price"],
            list_price=list_price,
            value_gap_pct=gap,
            confidence_score=r.get("confidence_score", 0),
            shap_top_driver=top_driver,
            created_at=str(r.get("created_at", "")),
        ))

    if params.get("undervalued_only"):
        results = [r for r in results if r.value_gap_pct is not None and r.value_gap_pct > 0]
        results.sort(key=lambda x: x.value_gap_pct or 0, reverse=True)

    results = results[:20]

    # Enrich top 5 results with neighborhood summary (one fetch per unique ZIP)
    zip_contexts: dict[str, str] = {}
    for r in results[:5]:
        z = r.zip_code
        if z and z not in zip_contexts:
            try:
                nd = fetch_neighborhood(z)
                parts = []
                if nd.get("walk_score"):
                    parts.append(f"Walk {nd['walk_score']}")
                if nd.get("school_rating"):
                    parts.append(f"Schools {nd['school_rating']}")
                zip_contexts[z] = " · ".join(parts) if parts else ""
            except Exception:
                zip_contexts[z] = ""
    for r in results[:5]:
        if r.zip_code:
            r.neighborhood_summary = zip_contexts.get(r.zip_code, "")

    return SearchResponse(results=results, query_parsed=params, total=len(results))
