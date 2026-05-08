from unittest.mock import patch, MagicMock


def _mock_httpx_response(json_data):
    resp = MagicMock()
    resp.json.return_value = json_data
    return resp


def test_fetch_neighborhood_returns_all_fields():
    from api.services.neighborhood import fetch_neighborhood
    with patch("api.services.neighborhood.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response([
            ["B19013_001E", "B01003_001E", "state", "zip code tabulation area"],
            ["72400", "45000", "48", "78704"],
        ])
        result = fetch_neighborhood("78704")
    assert result["zip_code"] == "78704"
    assert "school_rating" in result
    assert "summary" in result
    assert isinstance(result["summary"], str)


def test_fetch_neighborhood_known_zip_has_school_rating():
    from api.services.neighborhood import fetch_neighborhood, _AUSTIN_SCHOOL_RATINGS
    with patch("api.services.neighborhood.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response([["B19013_001E", "B01003_001E"], ["65000", "40000"]])
        result = fetch_neighborhood("78746")
    assert result["school_rating"] == _AUSTIN_SCHOOL_RATINGS["78746"]


def test_fetch_neighborhood_unknown_zip_returns_na():
    from api.services.neighborhood import fetch_neighborhood
    with patch("api.services.neighborhood.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response([["B19013_001E", "B01003_001E"], ["60000", "35000"]])
        result = fetch_neighborhood("99999")
    assert result["school_rating"] == "N/A"


def test_fetch_neighborhood_handles_http_error_gracefully():
    from api.services.neighborhood import fetch_neighborhood
    with patch("api.services.neighborhood.httpx.get", side_effect=Exception("timeout")):
        result = fetch_neighborhood("78704")
    assert result["zip_code"] == "78704"
    assert result["median_income"] is None
