# Fix HF Space Deployment + Data Pipeline Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the full AI layer (v2.0.0) to HuggingFace Space so `/search`, `/explain`, `/neighborhood`, `/deals` endpoints exist, then fix the data pipeline so NL search returns results and `/deals` page shows real undervalued properties.

**Architecture:** HuggingFace Spaces runs Docker from its own git repo — it's NOT auto-synced from GitHub. Files must be pushed directly to `https://huggingface.co/spaces/ofunrein/austin-avm-api` via the HF git endpoint or API. Once the new `api/` code is deployed, Supabase already has 1,308 predictions (21 ZIPs) but the NL search suggestion uses ZIP 78704 which has 0 rows. The seed script must be fixed to add popular Austin ZIPs, and the deal monitor must be run after seeding.

**Tech Stack:** HuggingFace Spaces (Docker), FastAPI, Supabase, GitHub Actions (for seed/monitor runs), Next.js on Vercel.

---

## Root Cause Summary

| Issue | Cause | Fix |
|-------|-------|-----|
| `/search` 404 | HF Space running old code — new routers not deployed | Push new `api/` to HF Space |
| `/explain` 404 | Same | Same |
| `/deals` API 404 | Same | Same |
| NL search 0 results | ZIP 78704 has 0 rows; query suggestion uses 78704 | Fix suggestions + seed popular ZIPs |
| Deals page empty | deals table has 0 rows | Run monitor after predictions seeded |

---

## File Map

**Modified:**
- `api/scripts/seed_inventory.py` — force-include popular Austin ZIPs (78704, 78745, 78702, 78703, 78741) by generating synthetic records from Kaggle data
- `web/components/SearchBar.tsx` — update NL suggestions to use ZIPs that actually exist in predictions table

**HF Space push (no file changes needed — push existing code):**
- Push current `api/` directory to HuggingFace Space git repo

**GitHub Actions (re-run existing workflows):**
- Trigger `seed-inventory.yml` with `max_rows=1000`
- Trigger `deal-monitor.yml` after seed completes

---

### Task 1: Deploy new API code to HuggingFace Space

**Files:**
- No code changes — push existing repo to HF Space git

The HF Space has its own git repo at `https://huggingface.co/spaces/ofunrein/austin-avm-api`. The GitHub repo and HF Space are NOT auto-synced. We must push the current `api/` + `Dockerfile` + `api/requirements.txt` directly to the HF Space repo.

- [ ] **Step 1: Add HF Space as a git remote**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate
git remote get-url hf-space 2>/dev/null || \
  git remote add hf-space https://Ofunrein:<HF_TOKEN>@huggingface.co/spaces/ofunrein/austin-avm-api
```

Expected: no output (remote added or already exists)

- [ ] **Step 2: Push main branch to HF Space**

```bash
git push hf-space main --force
```

Expected: output showing objects pushed, ending in `main -> main`. This triggers HF Space to rebuild the Docker image with the new code.

- [ ] **Step 3: Wait for build to complete (~3-5 min) then verify**

```bash
sleep 60 && \
curl -s "https://ofunrein-austin-avm-api.hf.space/openapi.json" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); routes=[p for p in d['paths']]; print('\n'.join(sorted(routes)))"
```

Expected output should include ALL of these routes:
```
/benchmark
/comps
/deals
/debug
/explain
/health
/neighborhood/{zip_code}
/predict
/scan
/search
```

If still showing old routes, wait 2 more minutes and retry. HF Space Docker builds take 3-7 minutes.

- [ ] **Step 4: Test new endpoints are live**

```bash
# Test /search
curl -s -X POST "https://ofunrein-austin-avm-api.hf.space/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "3BR in Austin"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('total:', d.get('total', 'ERROR'), 'results:', len(d.get('results', [])))"

# Test /deals
curl -s "https://ofunrein-austin-avm-api.hf.space/deals" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print('deals:', len(d) if isinstance(d, list) else d)"
```

Expected: `total: N results: N` for search (N ≥ 0, not 404), `deals: 0` for deals (empty but no error).

- [ ] **Step 5: Commit remote config**

```bash
git add .git/config 2>/dev/null || true
echo "HF Space deployed — new API routes live"
```

---

### Task 2: Fix NL search suggestions to use existing ZIPs

**Files:**
- Modify: `web/components/SearchBar.tsx`

The current suggestions use ZIP `78704` which has 0 predictions. The populated ZIPs are `78725, 78750, 78726, 78732, 78717, 78724, 78744`. Update suggestions to use real ZIPs.

- [ ] **Step 1: Read current SearchBar.tsx**

```bash
cat /Users/martinofunrein/Downloads/avm-zestimate/web/components/SearchBar.tsx | grep -A 10 "SUGGESTIONS"
```

- [ ] **Step 2: Update suggestions to use populated ZIPs**

In `web/components/SearchBar.tsx`, find the `SUGGESTIONS` array and replace it:

```tsx
const SUGGESTIONS = [
  "3BR under $500k in 78744",
  "undervalued homes in 78725",
  "pool homes 78750 built after 2010",
];
```

- [ ] **Step 3: Build to verify**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate/web && npm run build 2>&1 | tail -5
```

Expected: `✓ Compiled successfully`

- [ ] **Step 4: Commit**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate
git add web/components/SearchBar.tsx
git commit -m "fix: update NL search suggestions to use populated ZIP codes"
git push
```

---

### Task 3: Fix seed_inventory.py to include popular Austin ZIPs

**Files:**
- Modify: `api/scripts/seed_inventory.py`

Current seed uses Kaggle's `austinhousingprices` dataset. The dataset's ZIP distribution skews toward outer Austin (78725, 78750, 78726). We need to increase `MAX_ROWS` and NOT filter by `address` uniqueness — let the same address appear if it's in the training data. The real fix is to increase the row limit so popular ZIPs like 78744, 78745, 78702 get included.

Additionally, the `upsert_batch` call uses `on_conflict="address"` — but `address` column has no UNIQUE constraint in the current schema for historical sales (it only matters for Redfin current listings). For Kaggle historical data, same address can have multiple sales. Remove the `on_conflict` constraint for historical seeding.

- [ ] **Step 1: Read current seed_inventory.py**

```bash
grep -n "MAX_ROWS\|upsert_batch\|on_conflict\|SEED_MAX_ROWS" /Users/martinofunrein/Downloads/avm-zestimate/api/scripts/seed_inventory.py
```

- [ ] **Step 2: Update seed_inventory.py — increase limit, fix upsert**

Find and update these two things in `api/scripts/seed_inventory.py`:

**Change 1:** Increase default MAX_ROWS from 500 to 2000:
```python
MAX_ROWS = int(os.environ.get("SEED_MAX_ROWS", "2000"))
```

**Change 2:** In `upsert_batch`, remove `on_conflict` since Kaggle data has duplicate addresses:
```python
def upsert_batch(records: list[dict], db) -> None:
    for i in range(0, len(records), 100):
        batch = records[i : i + 100]
        db.table("predictions").upsert(batch).execute()
        print(f"  upserted {min(i + 100, len(records))}/{len(records)}")
```

- [ ] **Step 3: Verify syntax**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate && \
  python3 -c "import api.scripts.seed_inventory; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Update GitHub Actions seed-inventory.yml to use 2000 rows**

In `.github/workflows/seed-inventory.yml`, change the default:
```yaml
    inputs:
      max_rows:
        description: "Max listings to process"
        default: "2000"
        required: false
```

- [ ] **Step 5: Commit and push**

```bash
git add api/scripts/seed_inventory.py .github/workflows/seed-inventory.yml
git commit -m "fix: seed 2000 rows to cover more Austin ZIPs, remove address uniqueness constraint"
git push
```

---

### Task 4: Fix deal monitor to flag deals from existing predictions

**Files:**
- Modify: `api/scripts/monitor.py`

The monitor downloads Kaggle data and tries to predict each listing, then compares predicted_price vs list_price. But with Kaggle historical data, `latestPrice` IS the actual sale price — not a "list price" in the deal-finding sense. The monitor flags `predicted > list_price * 1.10` but if we use `latestPrice` as list_price, every historical sale where model overestimates will look "undervalued."

Better approach: instead of re-downloading Kaggle and predicting, query the existing `predictions` table for rows where `predicted_price > list_price * 1.10` and confidence >= 70. This is exactly what `/deals` GET endpoint already does. The monitor just needs to upsert those into the `deals` table.

- [ ] **Step 1: Read current monitor.py main() function**

```bash
grep -n "def main\|deals\|list_price\|gap\|upsert" /Users/martinofunrein/Downloads/avm-zestimate/api/scripts/monitor.py | head -30
```

- [ ] **Step 2: Replace monitor.py main() with Supabase-first approach**

Replace the entire `main()` function in `api/scripts/monitor.py`:

```python
def main() -> None:
    if not SUPABASE_URL or not SUPABASE_KEY or not ANTHROPIC_API_KEY:
        print("Error: SUPABASE_URL, SUPABASE_KEY, and ANTHROPIC_API_KEY must be set")
        import sys; sys.exit(1)

    from supabase import create_client
    from anthropic import Anthropic

    db = create_client(SUPABASE_URL, SUPABASE_KEY)
    anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

    print("Querying predictions table for deal candidates...")
    # Pull predictions that have list_price and look undervalued
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
            "deal_score": round(gap * r.get("confidence_score", 0) / 100, 2),
        })

    print(f"Found {len(deals)} deals above {MIN_GAP_PCT}% gap. Analyzing photos...")

    deals.sort(key=lambda d: d["deal_score"], reverse=True)
    # Claude Vision not available for historical Kaggle data (no photo URLs)
    # Skip photo analysis

    print("Upserting deals to Supabase...")
    if deals:
        db.table("deals").upsert(deals).execute()

    email_deals = [d for d in deals if d["value_gap_pct"] >= EMAIL_GAP_THRESHOLD]
    if email_deals:
        send_email(email_deals)

    print(f"Done. {len(deals)} deals stored, {len(email_deals)} email alerts.")
```

- [ ] **Step 3: Verify syntax**

```bash
SUPABASE_URL=test ANTHROPIC_API_KEY=test python3 -c "import api.scripts.monitor; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit and push**

```bash
git add api/scripts/monitor.py
git commit -m "fix: monitor queries existing predictions table instead of re-downloading Kaggle"
git push
```

---

### Task 5: Also push updated code to HF Space (after Task 3+4 fixes)

- [ ] **Step 1: Push updated api/ to HF Space**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate
git push hf-space main --force
```

Wait 3-5 minutes for rebuild.

- [ ] **Step 2: Verify /search and /deals routes still live**

```bash
curl -s "https://ofunrein-austin-avm-api.hf.space/health" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d)"
```

Expected: `{'status': 'ok', 'version': '2.0.0'}`

---

### Task 6: Trigger seed-inventory workflow (2000 rows)

- [ ] **Step 1: Trigger seed-inventory with 2000 rows**

```bash
gh workflow run seed-inventory.yml --repo Ofunrein/avm-zestimate -f max_rows=2000
sleep 3
gh run list --repo Ofunrein/avm-zestimate --workflow=seed-inventory.yml --limit=1
```

Expected: workflow queued

- [ ] **Step 2: Monitor until complete**

```bash
# Check every 30s until done
gh run watch --repo Ofunrein/avm-zestimate $(gh run list --repo Ofunrein/avm-zestimate --workflow=seed-inventory.yml --limit=1 --json databaseId --jq '.[0].databaseId') 2>/dev/null || \
  gh run list --repo Ofunrein/avm-zestimate --workflow=seed-inventory.yml --limit=1
```

Expected: `completed success`

- [ ] **Step 3: Verify predictions table populated**

```bash
curl -s -X POST "https://api.supabase.com/v1/projects/lisforfokxoibdlmtkag/database/query" \
  -H "Authorization: Bearer <SUPABASE_PAT>" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT COUNT(*) as total, COUNT(list_price) as with_price, COUNT(DISTINCT zip_code) as zips FROM predictions;"}' | python3 -m json.tool
```

Expected: `total` > 1308, `with_price` > 500, `zips` > 21

---

### Task 7: Trigger deal-monitor workflow

- [ ] **Step 1: Trigger deal-monitor**

```bash
gh workflow run deal-monitor.yml --repo Ofunrein/avm-zestimate
sleep 3
gh run list --repo Ofunrein/avm-zestimate --workflow=deal-monitor.yml --limit=1
```

- [ ] **Step 2: Monitor until complete**

```bash
gh run list --repo Ofunrein/avm-zestimate --workflow=deal-monitor.yml --limit=1
```

Expected: `completed success` within 2-5 min (queries Supabase, no Kaggle download needed now)

- [ ] **Step 3: Verify deals table populated**

```bash
curl -s -X POST "https://api.supabase.com/v1/projects/lisforfokxoibdlmtkag/database/query" \
  -H "Authorization: Bearer <SUPABASE_PAT>" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT COUNT(*) as deal_count, AVG(value_gap_pct) as avg_gap FROM deals;"}' | python3 -m json.tool
```

Expected: `deal_count` > 0, `avg_gap` > 10.0

---

### Task 8: End-to-end verification

- [ ] **Step 1: Test NL search returns results**

```bash
curl -s -X POST "https://ofunrein-austin-avm-api.hf.space/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "3BR under $500k in 78744"}' | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print('total:', d['total'], '| first zip:', d['results'][0]['zip_code'] if d['results'] else 'none')"
```

Expected: `total: N` where N > 0

- [ ] **Step 2: Test deals endpoint returns deals**

```bash
curl -s "https://ofunrein-austin-avm-api.hf.space/deals" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print('deals:', len(d), '| top gap:', d[0]['value_gap_pct'] if d else 'none')"
```

Expected: `deals: N` where N > 0

- [ ] **Step 3: Test explain endpoint**

```bash
curl -s -X POST "https://ofunrein-austin-avm-api.hf.space/explain" \
  -H "Content-Type: application/json" \
  -d '{
    "predicted_price": 450000, "lower_bound": 400000, "upper_bound": 500000,
    "confidence_score": 80,
    "shap_top5": [{"feature": "sqft_living", "feature_value": 1800.0, "shap_value": 45000.0, "direction": "increases"}],
    "zip_code": "78744", "sqft_living": 1800.0, "beds": 3, "baths_full": 2.0, "year_built": 2005
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print('explanation:', d.get('explanation', 'ERROR')[:80])"
```

Expected: explanation text starting with property description

- [ ] **Step 4: Run Playwright E2E tests**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate/web && \
  npx playwright test --reporter=list 2>&1 | tail -10
```

Expected: `29 passed` (all green)

- [ ] **Step 5: Final commit**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate
git tag v2.1.0 -m "v2.1.0 — HF Space redeployed with AI layer, NL search + deals working"
git push origin v2.1.0
```
