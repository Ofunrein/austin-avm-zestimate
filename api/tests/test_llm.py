import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")


def _mock_anthropic_response(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    client = MagicMock()
    client.messages.create.return_value = msg
    return client


def test_explain_prediction_returns_string():
    from api.services.llm import explain_prediction
    mock_client = _mock_anthropic_response("This home is valued at $453k. Strong buy signal.")
    with patch("api.services.llm._get_client", return_value=mock_client):
        result = explain_prediction(
            predicted_price=453235,
            lower_bound=398000,
            upper_bound=512000,
            confidence_score=82,
            shap_top5=[
                {"feature": "sqft_living", "feature_value": 1850.0, "shap_value": 45000.0, "direction": "increases"},
            ],
            zip_code="78704",
            sqft=1850.0,
            beds=3,
            baths=2.0,
            year_built=1978,
        )
    assert isinstance(result, str)
    assert len(result) > 10


def test_explain_prediction_includes_neighborhood():
    from api.services.llm import explain_prediction
    mock_client = _mock_anthropic_response("Walk Score 89. Fair value.")
    with patch("api.services.llm._get_client", return_value=mock_client):
        explain_prediction(
            predicted_price=450000,
            lower_bound=400000,
            upper_bound=500000,
            confidence_score=75,
            shap_top5=[],
            zip_code="78704",
            sqft=1500.0,
            beds=3,
            baths=2.0,
            year_built=2000,
            neighborhood_context="Walk Score 89, school rating B",
        )
    call_args = mock_client.messages.create.call_args
    prompt = call_args[1]["messages"][0]["content"]
    assert "Walk Score 89" in prompt


def test_parse_search_query_returns_dict():
    from api.services.llm import parse_search_query
    mock_client = _mock_anthropic_response(
        '{"beds_min": 3, "price_max": 400000, "zip_codes": ["78704"], "undervalued_only": false}'
    )
    with patch("api.services.llm._get_client", return_value=mock_client):
        result = parse_search_query("3BR under $400k in 78704")
    assert isinstance(result, dict)
    assert result.get("beds_min") == 3


def test_parse_search_query_handles_markdown_fences():
    from api.services.llm import parse_search_query
    mock_client = _mock_anthropic_response(
        "```json\n{\"beds_min\": 2, \"undervalued_only\": true}\n```"
    )
    with patch("api.services.llm._get_client", return_value=mock_client):
        result = parse_search_query("undervalued 2BR")
    assert result["beds_min"] == 2
    assert result["undervalued_only"] is True


def test_explain_request_schema_validates():
    from api.schemas import ExplainRequest
    req = ExplainRequest(
        predicted_price=450000,
        lower_bound=400000,
        upper_bound=500000,
        confidence_score=80,
        shap_top5=[],
        zip_code="78704",
        sqft_living=1800.0,
        beds=3,
        baths_full=2.0,
        year_built=2005,
    )
    assert req.zip_code == "78704"


def test_search_response_schema():
    from api.schemas import SearchResponse, SearchResult
    result = SearchResult(
        id="abc",
        predicted_price=450000,
        confidence_score=80,
    )
    resp = SearchResponse(results=[result], query_parsed={}, total=1)
    assert resp.total == 1
