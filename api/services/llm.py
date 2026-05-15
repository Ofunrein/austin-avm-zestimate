import json
import os
from openai import OpenAI

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        )
    return _client


def explain_prediction(
    predicted_price: int,
    lower_bound: int,
    upper_bound: int,
    confidence_score: int,
    shap_top5: list[dict],
    zip_code: str,
    sqft: float,
    beds: int,
    baths: float,
    year_built: int,
    neighborhood_context: str = "",
) -> str:
    shap_lines = "\n".join(
        f"  {f['feature']}: {'+' if f['shap_value'] > 0 else ''}{f['shap_value']:,.0f} ({f['direction']} value)"
        for f in shap_top5
    )
    prompt = (
        "You are a real estate analyst. Given SHAP feature contributions and neighborhood context, "
        "write a 2-3 sentence explanation of this Austin TX home valuation in plain English. "
        "Be specific about dollar amounts. End with a one-sentence market signal "
        "(strong buy / fair value / overpriced).\n\n"
        f"Property: {sqft:.0f} sqft, {beds}BR/{baths}BA, built {year_built}, ZIP {zip_code}\n"
        f"Predicted: ${predicted_price:,} (range: ${lower_bound:,}–${upper_bound:,}, {confidence_score}% confidence)\n"
        f"Key value drivers:\n{shap_lines}\n"
        f"Neighborhood: {neighborhood_context or 'No neighborhood data available'}"
    )
    resp = _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=150,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


def parse_search_query(query: str) -> dict:
    prompt = (
        "Extract search parameters from this Austin TX real estate query. Return JSON only, no explanation.\n"
        'Schema: {"beds_min": int|null, "baths_min": float|null, "sqft_min": int|null, '
        '"sqft_max": int|null, "price_max": int|null, "zip_codes": [str]|null, '
        '"undervalued_only": bool, "year_built_min": int|null}\n'
        "Only return fields from this schema. Do not add has_pool or other unsupported fields.\n"
        f"Query: {query}"
    )
    resp = _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=200,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.choices[0].message.content.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)
