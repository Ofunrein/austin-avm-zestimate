#!/usr/bin/env python3
"""
Weekly deal monitor: download Redfin Austin listings, predict, flag undervalued,
analyze listing photos via Claude Vision, store in deals table, send SendGrid email.

Required env vars:
  ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY, API_BASE
Optional:
  SENDGRID_API_KEY, ALERT_EMAIL (for email alerts)
"""
import base64
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

MIN_GAP_PCT = float(os.environ.get("MIN_GAP_PCT", "5.0"))
MIN_CONFIDENCE = int(os.environ.get("MIN_CONFIDENCE", "0"))
MAX_LISTINGS = int(os.environ.get("MAX_LISTINGS", "200"))
EMAIL_GAP_THRESHOLD = float(os.environ.get("EMAIL_GAP_THRESHOLD", "15.0"))

API_BASE = os.environ.get("API_BASE", "https://ofunrein-austin-avm-api.hf.space")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")


def analyze_photo(photo_url: str, anthropic_client) -> str | None:
    if not photo_url or not photo_url.startswith("http"):
        return None
    try:
        req = urllib.request.Request(photo_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            img_data = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
            _VALID_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
            if content_type not in _VALID_IMAGE_TYPES:
                return None
    except Exception:
        return None

    b64 = base64.standard_b64encode(img_data).decode()
    try:
        msg = anthropic_client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=80,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": content_type, "data": b64},
                    },
                    {
                        "type": "text",
                        "text": "Describe the condition and notable features of this Austin TX home listing photo in 1 sentence.",
                    },
                ],
            }],
        )
        return msg.content[0].text.strip()
    except Exception:
        return None


def send_email(deals: list[dict]) -> None:
    if not SENDGRID_API_KEY or not ALERT_EMAIL or not deals:
        return
    top5 = deals[:5]
    lines = [f"Austin AVM found {len(deals)} undervalued properties this week.\n\nTop deals:\n"]
    for d in top5:
        lines.append(
            f"  {d['address']} ({d['zip_code']})\n"
            f"  List: ${d['list_price']:,} | Predicted: ${d['predicted_price']:,}"
            f" | Gap: +{d['value_gap_pct']:.1f}%\n"
        )
    payload = json.dumps({
        "personalizations": [{"to": [{"email": ALERT_EMAIL}]}],
        "from": {"email": ALERT_EMAIL},
        "subject": f"\U0001f3e0 {len(deals)} Austin deals found — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "content": [{"type": "text/plain", "value": "\n".join(lines)}],
    }).encode()
    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print(f"Alert sent to {ALERT_EMAIL}")
    except Exception as e:
        print(f"Email failed: {e}")


def main() -> None:
    if not SUPABASE_URL or not SUPABASE_KEY or not ANTHROPIC_API_KEY:
        print("Error: SUPABASE_URL, SUPABASE_KEY, and ANTHROPIC_API_KEY must be set")
        import sys; sys.exit(1)

    from supabase import create_client

    db = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("Querying predictions table for deal candidates...")
    rows = (
        db.table("predictions")
        .select("id,address,zip_code,list_price,predicted_price,confidence_score,beds,baths_full,sqft_living,year_built,shap_json")
        .not_.is_("list_price", "null")
        .gte("confidence_score", MIN_CONFIDENCE)
        .limit(500)
        .execute()
        .data
    )
    print(f"{len(rows)} predictions with list_price found")

    deals: list[dict] = []
    for r in rows:
        list_price = r.get("list_price")
        predicted = r.get("predicted_price", 0)
        if not list_price or list_price <= 0:
            continue
        gap = round((predicted - list_price) / list_price * 100, 1)
        if gap < MIN_GAP_PCT:
            continue
        shap_json = r.get("shap_json") or []
        shap_driver = shap_json[0]["feature"] if shap_json else None
        deals.append({
            "address": r.get("address"),
            "zip_code": r.get("zip_code"),
            "list_price": list_price,
            "predicted_price": predicted,
            "value_gap_pct": gap,
            "confidence_score": r.get("confidence_score", 0),
            "beds": r.get("beds"),
            "baths_full": r.get("baths_full"),
            "sqft_living": r.get("sqft_living"),
            "year_built": r.get("year_built"),
            "shap_top_driver": shap_driver,
            "deal_score": round(gap * r.get("confidence_score", 1) / 100, 2),
            "data_source": r.get("data_source", "kaggle_historical"),
        })

    print(f"Found {len(deals)} historical value opportunities above {MIN_GAP_PCT}% gap.")
    deals.sort(key=lambda d: d["deal_score"], reverse=True)

    print("Upserting deals to Supabase...")
    if deals:
        try:
            db.table("deals").upsert(deals).execute()
        except Exception as e:
            print(f"UPSERT_ERROR_REPR: {e!r}")
            print(f"UPSERT_ERROR_STR: {e}")
            raise

    email_deals = [d for d in deals if d["value_gap_pct"] >= EMAIL_GAP_THRESHOLD]
    if email_deals:
        send_email(email_deals)

    print(f"Done. {len(deals)} deals stored, {len(email_deals)} email alerts.")


if __name__ == "__main__":
    main()
