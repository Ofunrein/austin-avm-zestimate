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

MIN_GAP_PCT = float(os.environ.get("MIN_GAP_PCT", "10.0"))
MIN_CONFIDENCE = int(os.environ.get("MIN_CONFIDENCE", "70"))
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
    from anthropic import Anthropic
    from api.scripts.seed_inventory import download_csv, parse_row, REDFIN_URL, predict_property

    db = create_client(SUPABASE_URL, SUPABASE_KEY)
    anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

    print("Downloading Redfin Austin listings...")
    rows = download_csv(REDFIN_URL)
    print(f"{len(rows)} listings downloaded. Processing up to {MAX_LISTINGS}...")

    deals: list[dict] = []
    for i, row in enumerate(rows[:MAX_LISTINGS]):
        parsed = parse_row(row)
        if not parsed or not parsed.get("list_price"):
            continue
        pred = predict_property(parsed)
        if not pred:
            continue

        list_price = parsed["list_price"]
        predicted = pred["predicted_price"]
        confidence = pred["confidence_score"]
        gap = round((predicted - list_price) / list_price * 100, 1)

        if gap >= MIN_GAP_PCT and confidence >= MIN_CONFIDENCE:
            shap_driver = pred["shap_top5"][0]["feature"] if pred["shap_top5"] else None
            deals.append({
                "address": parsed["address"],
                "zip_code": parsed["zip_code"],
                "list_price": list_price,
                "predicted_price": predicted,
                "value_gap_pct": gap,
                "confidence_score": confidence,
                "beds": parsed["beds"],
                "baths_full": parsed["baths_full"],
                "sqft_living": parsed["sqft_living"],
                "year_built": parsed["year_built"],
                "photo_url": parsed.get("photo_url"),
                "shap_top_driver": shap_driver,
                "deal_score": round(gap * confidence / 100, 2),
            })

        if (i + 1) % 50 == 0:
            print(f"  processed {i + 1}/{min(MAX_LISTINGS, len(rows))}")
        time.sleep(0.05)

    print(f"Found {len(deals)} deals above {MIN_GAP_PCT}% gap. Analyzing photos...")

    deals.sort(key=lambda d: d["deal_score"], reverse=True)
    for deal in deals[:20]:
        note = analyze_photo(deal.get("photo_url", ""), anthropic)
        deal["condition_note"] = note
        if note:
            print(f"  Photo analyzed: {deal['address'][:30]}...")

    print("Upserting deals to Supabase...")
    if deals:
        db.table("deals").upsert(deals, on_conflict="address").execute()

    email_deals = [d for d in deals if d["value_gap_pct"] >= EMAIL_GAP_THRESHOLD]
    if email_deals:
        send_email(email_deals)

    print(f"Done. {len(deals)} deals stored, {len(email_deals)} email alerts.")


if __name__ == "__main__":
    main()
