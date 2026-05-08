# HF Space API Wiring, E2E Testing, and PR Merge

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to run this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Complete tasks sequentially unless a parallel window is noted.

**Goal:** Confirm the live HuggingFace Space API is healthy, verify Docker import paths, update docs with live URLs, pass CI, apply the Supabase schema, run a full E2E smoke test across every live endpoint, merge PR #1 to main, and tag v1.0.0.

**Architecture reference:**
- HF Space (Docker API): `https://ofunrein-austin-avm-api.hf.space`
- HF Model repo: `https://huggingface.co/ofunrein/austin-avm-model`
- Vercel frontend: `https://austin-avm.vercel.app`
- GitHub repo: `Ofunrein/avm-zestimate`, branch `dev/implementation`, PR #1

**Key path facts (from source):**
- `Dockerfile` at repo root: `COPY ml/src/ ./ml/src/` and `COPY api/ ./api/`, `WORKDIR /app`
- Each router uses `sys.path.insert(0, str(Path(__file__).parents[3] / "ml/src"))`. Inside Docker `WORKDIR /app`, `__file__` for `predict.py` resolves to `/app/api/routers/predict.py`. `parents[3]` = `/app`. So the insert becomes `/app/ml/src` — matching the `COPY` destination exactly.
- `api/main.py` imports via `api.routers.*` (package-relative). `uvicorn api.main:app` is invoked from `/app`. Both are correct assuming `/app` is on `PYTHONPATH`, which uvicorn sets implicitly when the module path is used.
- `model_loader.py` loads from HF Hub when `HF_REPO_ID` env var is set (Space secret).

---

## Task 1: Verify HF Space Health

**What:** Poll `/health` until the Space is live, then probe all four endpoints with known-good payloads.

**Why:** HF Docker Spaces have a cold-start window of 30–120 s after a new build. A non-200 or timeout here blocks all downstream tasks.

- [ ] **Step 1: Poll health until ok (max 3 min)**

```bash
for i in $(seq 1 18); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    https://ofunrein-austin-avm-api.hf.space/health)
  BODY=$(curl -s https://ofunrein-austin-avm-api.hf.space/health)
  echo "[$i] HTTP $STATUS — $BODY"
  [ "$STATUS" = "200" ] && echo "Space is up." && break
  sleep 10
done
```

Expected final line: `HTTP 200 — {"status":"ok","version":"1.0.0"}`

Record actual cold-start time: number of 10-second intervals before first 200.

- [ ] **Step 2: Test /predict**

```bash
curl -s -X POST https://ofunrein-austin-avm-api.hf.space/predict \
  -H "Content-Type: application/json" \
  -d '{
    "sqft_living": 1800,
    "beds": 3,
    "baths_full": 2,
    "baths_half": 0,
    "year_built": 2005,
    "zip_code": "78701",
    "lat": 30.27,
    "lng": -97.74,
    "lot_sqft": 6000,
    "garage_spaces": 1,
    "has_pool": 0,
    "stories": 1,
    "assessed_value": 0
  }' | python3 -m json.tool
```

Expected: JSON object containing `predicted_price`, `lower_bound`, `upper_bound`, `confidence_score` (all integers), `shap_top5` (array of 5 objects with `feature`, `feature_value`, `shap_value`, `direction`), `model_version` (string).

- [ ] **Step 3: Test /benchmark**

```bash
curl -s https://ofunrein-austin-avm-api.hf.space/benchmark | python3 -m json.tool
```

Expected: JSON with `model_version`, `test_medape` (float), `test_mae`, `test_rmse`, `test_within_5pct`, `test_within_10pct`, `n_test` (int), `by_zip` (array). If models are present, `model_version` is not `"not-trained"`.

- [ ] **Step 4: Test /comps**

```bash
curl -s "https://ofunrein-austin-avm-api.hf.space/comps?lat=30.27&lng=-97.74&sqft=1800&beds=3&bath_total=2.0&year_built=2005&n=5" \
  | python3 -m json.tool
```

Expected: JSON array of up to 5 objects, each with `sale_price`, `sqft_living`, `similarity_score`. May return `[]` if processed parquet not deployed to Space (acceptable — comps reads from `ml/data/processed/train_features.parquet` which is not in the Docker image; empty is valid).

- [ ] **Step 5: Test /scan**

```bash
curl -s -X POST https://ofunrein-austin-avm-api.hf.space/scan \
  -H "Content-Type: application/json" \
  -d '{
    "properties": [
      {
        "sqft_living": 1800, "beds": 3, "baths_full": 2, "baths_half": 0,
        "year_built": 2005, "zip_code": "78701", "lat": 30.27, "lng": -97.74,
        "lot_sqft": 6000, "garage_spaces": 1, "has_pool": 0, "stories": 1,
        "assessed_value": 0, "list_price": 380000
      },
      {
        "sqft_living": 2200, "beds": 4, "baths_full": 3, "baths_half": 0,
        "year_built": 2010, "zip_code": "78702", "lat": 30.28, "lng": -97.73,
        "lot_sqft": 7500, "garage_spaces": 2, "has_pool": 0, "stories": 2,
        "assessed_value": 0, "list_price": 520000
      }
    ]
  }' | python3 -m json.tool
```

Expected: JSON array of 2 objects sorted by `value_gap_pct` descending, each with `index`, `predicted_price`, `list_price`, `value_gap_pct`, `is_undervalued`, `shap_top_driver`.

- [ ] **Step 6: Test OpenAPI docs page**

```bash
curl -s -o /dev/null -w "%{http_code}" \
  https://ofunrein-austin-avm-api.hf.space/docs
```

Expected: `200`

---

## Task 2: Verify Docker Import Path Correctness

**What:** Confirm that `sys.path.insert` in routers resolves to the correct directory inside the Docker container, or fix it if not.

**Analysis (already verified from source):**

Inside Docker (`WORKDIR /app`):
- `predict.py` absolute path: `/app/api/routers/predict.py`
- `Path(__file__)` = `/app/api/routers/predict.py`
- `.parents[0]` = `/app/api/routers`
- `.parents[1]` = `/app/api`
- `.parents[2]` = `/app`
- `.parents[3]` = `/` ← **BUG**: `parents[3]` of a 4-segment path is `/`, not `/app`

Wait — `/app/api/routers/predict.py` has segments: `app`, `api`, `routers`, `predict.py`. `parents` in Python's `Path`:
- `parents[0]` = `/app/api/routers`
- `parents[1]` = `/app/api`
- `parents[2]` = `/app`
- `parents[3]` = `/`

So `Path(__file__).parents[3] / "ml/src"` = `/ml/src` inside Docker, but the copy lands at `/app/ml/src`. **This is the import path bug.**

**Fix needed in three router files** (`predict.py`, `comps.py`, `scan.py`): change `parents[3]` to `parents[2]`.

- [ ] **Step 1: Verify the bug is present**

```bash
grep -n "parents\[3\]" \
  /Users/martinofunrein/Downloads/avm-zestimate/api/routers/predict.py \
  /Users/martinofunrein/Downloads/avm-zestimate/api/routers/comps.py \
  /Users/martinofunrein/Downloads/avm-zestimate/api/routers/scan.py
```

Expected: 3 matching lines showing `parents[3]`.

- [ ] **Step 2: Apply fix**

In `/Users/martinofunrein/Downloads/avm-zestimate/api/routers/predict.py`, line 7:

Change:
```python
sys.path.insert(0, str(Path(__file__).parents[3] / "ml/src"))
```
To:
```python
sys.path.insert(0, str(Path(__file__).parents[2] / "ml/src"))
```

Same change in `comps.py` line 6 and `scan.py` line 7.

- [ ] **Step 3: Verify no other `parents[N]` references exist in routers**

```bash
grep -rn "sys.path" \
  /Users/martinofunrein/Downloads/avm-zestimate/api/
```

Expected: only the three routers, all now using `parents[2]`.

- [ ] **Step 4: Verify locally (if ml venv available)**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate
python3 -c "
from pathlib import Path
f = Path('/app/api/routers/predict.py')
print('parents[2]:', f.parents[2] / 'ml/src')
print('parents[3]:', f.parents[3] / 'ml/src')
"
```

Expected output:
```
parents[2]: /app/ml/src
parents[3]: /ml/src
```

- [ ] **Step 5: Commit and push the fix**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate
git add api/routers/predict.py api/routers/comps.py api/routers/scan.py
git commit -m "fix: correct sys.path parents index for Docker WORKDIR /app"
git push origin dev/implementation
```

Expected: push succeeds, GitHub Actions CI triggers on `dev/implementation`.

Note: After pushing, the HF Space will rebuild automatically if connected to the GitHub repo branch. Wait for rebuild before re-running Task 1 Step 1-5 to confirm the fix takes effect live.

---

## Task 3: Update DEPLOY.md with Live URLs

**What:** Replace generic placeholder text in `DEPLOY.md` with the actual live URLs.

- [ ] **Step 1: Open DEPLOY.md and append live URLs section**

Edit `/Users/martinofunrein/Downloads/avm-zestimate/DEPLOY.md`.

Append after the existing content:

```markdown

## Live Deployment URLs

| Service | URL |
|---------|-----|
| Frontend (Vercel) | https://austin-avm.vercel.app |
| API (HF Space) | https://ofunrein-austin-avm-api.hf.space |
| API docs (Swagger) | https://ofunrein-austin-avm-api.hf.space/docs |
| HF model repo | https://huggingface.co/ofunrein/austin-avm-model |
| GitHub repo | https://github.com/Ofunrein/avm-zestimate |
```

- [ ] **Step 2: Commit**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate
git add DEPLOY.md
git commit -m "docs: add live deployment URLs to DEPLOY.md"
git push origin dev/implementation
```

Expected: clean push.

---

## Task 4: Run Full CI on dev/implementation

**What:** Trigger the GitHub Actions CI workflow and confirm both jobs pass.

- [ ] **Step 1: Trigger CI (or confirm auto-trigger from Task 2 push)**

```bash
gh workflow run ci.yml --repo Ofunrein/avm-zestimate --ref dev/implementation
```

If already triggered by the Task 2 push, skip this step — CI fires automatically on pushes to `dev/implementation` per `.github/workflows/ci.yml`.

- [ ] **Step 2: Wait for CI to complete**

```bash
gh run list --repo Ofunrein/avm-zestimate --branch dev/implementation --limit 5
```

Poll every 30 seconds until both jobs show `completed`:

```bash
RUN_ID=$(gh run list --repo Ofunrein/avm-zestimate --branch dev/implementation \
  --limit 1 --json databaseId -q '.[0].databaseId')
gh run watch "$RUN_ID" --repo Ofunrein/avm-zestimate
```

- [ ] **Step 3: Verify both jobs passed**

```bash
gh run view "$RUN_ID" --repo Ofunrein/avm-zestimate
```

Expected output includes:
```
JOBS
✓ ml-tests    ...    completed    success
✓ web-build   ...    completed    success
```

- [ ] **Step 4: If ml-tests fails — diagnose**

```bash
gh run view "$RUN_ID" --repo Ofunrein/avm-zestimate --log-failed
```

Common failure causes:
- Missing `libgomp1` (already in CI workflow, should not occur)
- Import error in `avm.*` modules — check `ml/src/avm/__init__.py`
- Pytest discovery error — check `ml/tests/` structure

- [ ] **Step 5: If web-build fails — diagnose**

```bash
gh run view "$RUN_ID" --repo Ofunrein/avm-zestimate --log-failed
```

Common failure: TypeScript type error surfaced by `npm run build`. Fix in `web/` then re-push.

---

## Task 5: Apply Supabase Schema

**What:** Execute `supabase/schema.sql` against the live Supabase project to create `predictions`, `benchmark_runs`, and `comps_cache` tables.

**Note:** This is a manual dashboard step — no Supabase CLI credentials are available and the project ref is not committed to the repo.

- [ ] **Step 1: Open Supabase SQL Editor**

Navigate to: `https://supabase.com/dashboard` → select your project → SQL Editor → New query.

- [ ] **Step 2: Paste and run the full schema**

The exact SQL to run (contents of `/Users/martinofunrein/Downloads/avm-zestimate/supabase/schema.sql`):

```sql
-- Run this in Supabase SQL editor at https://supabase.com/dashboard

create table if not exists predictions (
  id uuid primary key default gen_random_uuid(),
  address text,
  lat numeric,
  lng numeric,
  sqft_living numeric,
  beds integer,
  baths_full numeric,
  year_built integer,
  zip_code text,
  predicted_price integer,
  lower_bound integer,
  upper_bound integer,
  confidence_score integer,
  shap_json jsonb,
  created_at timestamptz default now()
);

create table if not exists benchmark_runs (
  id uuid primary key default gen_random_uuid(),
  model_version text not null,
  medape numeric,
  mae numeric,
  rmse numeric,
  within_5pct numeric,
  within_10pct numeric,
  n_test integer,
  test_period text,
  residuals_json jsonb,
  created_at timestamptz default now()
);

create table if not exists comps_cache (
  cache_key text primary key,
  comps_json jsonb not null,
  created_at timestamptz default now()
);

-- indexes for benchmark dashboard and lookup performance
create index if not exists idx_predictions_zip on predictions(zip_code);
create index if not exists idx_predictions_created on predictions(created_at desc);
create index if not exists idx_benchmark_created on benchmark_runs(created_at desc);
```

Click "Run". Expected output: `Success. No rows returned.`

- [ ] **Step 3: Verify tables exist**

Run in SQL Editor:

```sql
select table_name from information_schema.tables
where table_schema = 'public'
order by table_name;
```

Expected result rows: `benchmark_runs`, `comps_cache`, `predictions`.

- [ ] **Step 4: Verify indexes exist**

```sql
select indexname, tablename from pg_indexes
where schemaname = 'public'
order by tablename, indexname;
```

Expected: `idx_benchmark_created`, `idx_predictions_created`, `idx_predictions_zip` plus the primary key indexes.

- [ ] **Step 5: Confirm Vercel env vars are set**

```bash
# Verify NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY exist in Vercel
gh api /v9/projects/austin-avm/env \
  -H "Authorization: Bearer $(cat ~/.vercel/auth.json 2>/dev/null | python3 -m json.tool | grep token | awk '{print $2}' | tr -d ',"')" \
  2>/dev/null | python3 -m json.tool | grep -E '"key"'
```

If that fails (no Vercel token in shell), check manually: Vercel dashboard → austin-avm → Settings → Environment Variables. Confirm `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set for Production.

---

## Task 6: E2E Smoke Test

**What:** Script that validates every live layer: Vercel frontend, HF Space health, and all four API endpoints.

- [ ] **Step 1: Run the full smoke test script**

```bash
#!/bin/bash
set -euo pipefail

VERCEL_URL="https://austin-avm.vercel.app"
HF_URL="https://ofunrein-austin-avm-api.hf.space"
PASS=0
FAIL=0

check() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo "PASS  $label (HTTP $actual)"
    PASS=$((PASS + 1))
  else
    echo "FAIL  $label — expected HTTP $expected, got $actual"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== AVM E2E Smoke Test ==="
echo "Vercel: $VERCEL_URL"
echo "HF:     $HF_URL"
echo ""

# Vercel frontend pages
check "Vercel /" "200" \
  "$(curl -s -o /dev/null -w "%{http_code}" "$VERCEL_URL/")"
check "Vercel /benchmark" "200" \
  "$(curl -s -o /dev/null -w "%{http_code}" "$VERCEL_URL/benchmark")"
check "Vercel /scanner" "200" \
  "$(curl -s -o /dev/null -w "%{http_code}" "$VERCEL_URL/scanner")"
check "Vercel /model-card" "200" \
  "$(curl -s -o /dev/null -w "%{http_code}" "$VERCEL_URL/model-card")"

# HF Space health
check "HF /health" "200" \
  "$(curl -s -o /dev/null -w "%{http_code}" "$HF_URL/health")"
HEALTH_BODY=$(curl -s "$HF_URL/health")
echo "      body: $HEALTH_BODY"

# HF /benchmark (GET)
check "HF /benchmark" "200" \
  "$(curl -s -o /dev/null -w "%{http_code}" "$HF_URL/benchmark")"

# HF /comps (GET with query params)
check "HF /comps" "200" \
  "$(curl -s -o /dev/null -w "%{http_code}" \
    "$HF_URL/comps?lat=30.27&lng=-97.74&sqft=1800&beds=3&bath_total=2.0&year_built=2005&n=3")"

# HF /predict (POST)
check "HF /predict" "200" \
  "$(curl -s -o /dev/null -w "%{http_code}" -X POST "$HF_URL/predict" \
    -H "Content-Type: application/json" \
    -d '{
      "sqft_living":1800,"beds":3,"baths_full":2,"baths_half":0,
      "year_built":2005,"zip_code":"78701","lat":30.27,"lng":-97.74,
      "lot_sqft":6000,"garage_spaces":1,"has_pool":0,"stories":1,"assessed_value":0
    }')"

# HF /scan (POST with 2 properties)
check "HF /scan" "200" \
  "$(curl -s -o /dev/null -w "%{http_code}" -X POST "$HF_URL/scan" \
    -H "Content-Type: application/json" \
    -d '{
      "properties":[
        {"sqft_living":1800,"beds":3,"baths_full":2,"baths_half":0,
         "year_built":2005,"zip_code":"78701","lat":30.27,"lng":-97.74,
         "lot_sqft":6000,"garage_spaces":1,"has_pool":0,"stories":1,
         "assessed_value":0,"list_price":380000},
        {"sqft_living":2200,"beds":4,"baths_full":3,"baths_half":0,
         "year_built":2010,"zip_code":"78702","lat":30.28,"lng":-97.73,
         "lot_sqft":7500,"garage_spaces":2,"has_pool":0,"stories":2,
         "assessed_value":0,"list_price":520000}
      ]
    }')"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && echo "ALL CLEAR — proceed to merge." || echo "FIX FAILURES before merging."
```

Save as `/tmp/avm-e2e-smoke.sh`, then:

```bash
chmod +x /tmp/avm-e2e-smoke.sh && /tmp/avm-e2e-smoke.sh
```

Expected output:
```
=== AVM E2E Smoke Test ===
Vercel: https://austin-avm.vercel.app
HF:     https://ofunrein-austin-avm-api.hf.space

PASS  Vercel / (HTTP 200)
PASS  Vercel /benchmark (HTTP 200)
PASS  Vercel /scanner (HTTP 200)
PASS  Vercel /model-card (HTTP 200)
PASS  HF /health (HTTP 200)
      body: {"status":"ok","version":"1.0.0"}
PASS  HF /benchmark (HTTP 200)
PASS  HF /comps (HTTP 200)
PASS  HF /predict (HTTP 200)
PASS  HF /scan (HTTP 200)

=== Results: 9 passed, 0 failed ===
ALL CLEAR — proceed to merge.
```

- [ ] **Step 2: Spot-check /predict response body for correctness**

```bash
curl -s -X POST https://ofunrein-austin-avm-api.hf.space/predict \
  -H "Content-Type: application/json" \
  -d '{
    "sqft_living":1800,"beds":3,"baths_full":2,"baths_half":0,
    "year_built":2005,"zip_code":"78701","lat":30.27,"lng":-97.74,
    "lot_sqft":6000,"garage_spaces":1,"has_pool":0,"stories":1,"assessed_value":0
  }' | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert isinstance(d['predicted_price'], int), 'predicted_price not int'
assert d['lower_bound'] < d['predicted_price'] < d['upper_bound'], 'CI sanity fail'
assert 0 <= d['confidence_score'] <= 100, 'confidence out of range'
assert len(d['shap_top5']) == 5, 'shap_top5 not 5 items'
for s in d['shap_top5']:
    assert s['direction'] in ('increases', 'decreases'), f'bad direction: {s}'
print('Body validation passed.')
print('predicted_price:', d['predicted_price'])
print('CI: [{lower_bound}, {upper_bound}]'.format(**d))
print('confidence_score:', d['confidence_score'])
print('model_version:', d['model_version'])
"
```

Expected: `Body validation passed.` followed by numeric output. If `predicted_price` is in the range $200,000–$900,000 for a 1800-sqft Austin home, the model is functioning correctly.

- [ ] **Step 3: If any check fails**

| Failure | Likely cause | Fix |
|---------|-------------|-----|
| HF /health returns 503 | Space still building or crashed | Check HF Space logs at https://huggingface.co/spaces/ofunrein/austin-avm-api → Logs tab |
| HF /predict returns 500 with import error | `parents[3]` bug not yet deployed | Confirm Task 2 fix pushed and Space rebuilt |
| HF /predict returns 500 with model load error | `HF_REPO_ID` secret not set or model files missing | Check Space Settings → Secrets; verify `ofunrein/austin-avm-model` exists on HF Hub |
| Vercel pages return 404 | Deployment not pointed to correct branch | Check Vercel dashboard → Project → Deployments |
| Vercel pages return 500 | `NEXT_PUBLIC_API_URL` env var missing or wrong | Set in Vercel dashboard → Settings → Environment Variables → `https://ofunrein-austin-avm-api.hf.space` |

---

## Task 7: Merge PR #1 to main

**Pre-condition:** Task 4 CI passed, Task 6 smoke test shows 0 failures.

- [ ] **Step 1: Verify PR is mergeable**

```bash
gh pr view 1 --repo Ofunrein/avm-zestimate
```

Expected output includes:
```
State: OPEN
...
Mergeable: MERGEABLE
```

Confirm `State: OPEN` and no merge conflicts.

- [ ] **Step 2: Confirm CI status on PR**

```bash
gh pr checks 1 --repo Ofunrein/avm-zestimate
```

Expected: both `ml-tests` and `web-build` show `pass`.

- [ ] **Step 3: Merge PR**

```bash
gh pr merge 1 --merge --repo Ofunrein/avm-zestimate
```

Expected output:
```
Merging pull request Ofunrein/avm-zestimate#1 (dev/implementation → main)
✓ Merged pull request #1
```

- [ ] **Step 4: Verify main is up to date**

```bash
git fetch origin main
git log origin/main --oneline -5
```

Expected: the most recent commits from `dev/implementation` now appear on `origin/main`.

---

## Task 8: Tag v1.0.0 Release

**Pre-condition:** PR #1 merged (Task 7 complete).

- [ ] **Step 1: Fetch latest main**

```bash
cd /Users/martinofunrein/Downloads/avm-zestimate
git fetch origin
git checkout main
git pull origin main
```

Expected: `Already up to date.` or fast-forward to latest merged commit.

- [ ] **Step 2: Tag the release**

```bash
git tag v1.0.0
git push origin v1.0.0
```

Expected:
```
Total 0 (delta 0), reused 0 (delta 0), pack-reused 0
To https://github.com/Ofunrein/avm-zestimate
 * [new tag]         v1.0.0 -> v1.0.0
```

- [ ] **Step 3: Verify tag on GitHub**

```bash
gh release view v1.0.0 --repo Ofunrein/avm-zestimate 2>/dev/null \
  || echo "No release object yet — tag pushed but no GitHub Release created."
```

```bash
gh api repos/Ofunrein/avm-zestimate/git/refs/tags/v1.0.0
```

Expected: JSON response containing `"ref": "refs/tags/v1.0.0"`.

- [ ] **Step 4: (Optional) Create GitHub Release with notes**

```bash
gh release create v1.0.0 \
  --repo Ofunrein/avm-zestimate \
  --title "v1.0.0 — Austin AVM Live" \
  --notes "Full stack live: HF Space API, Vercel frontend, Supabase schema applied. XGBoost + LightGBM ensemble with SHAP explanations, confidence intervals, comps finder, and portfolio scanner."
```

Expected: URL to the new release page on GitHub.

---

## Dependency Order

```
Task 2 (fix import paths)
  └─> push to dev/implementation
        ├─> Task 4 (CI runs automatically on push)
        └─> HF Space rebuilds (for Task 1 re-verification)

Task 1 (verify HF health) — run after Space rebuild from Task 2 push
Task 3 (update DEPLOY.md) — can run in parallel with Task 4
Task 5 (Supabase schema) — independent, run any time

Task 6 (E2E smoke test)
  └─> requires Task 1 (API up) + Task 4 (CI green)

Task 7 (merge PR)
  └─> requires Task 4 CI pass + Task 6 all-clear

Task 8 (tag v1.0.0)
  └─> requires Task 7 (main has merged code)
```

Critical path: Task 2 push → CI green (Task 4) → E2E pass (Task 6) → merge (Task 7) → tag (Task 8).
Tasks 3 and 5 are independent of the critical path and can run at any point.
