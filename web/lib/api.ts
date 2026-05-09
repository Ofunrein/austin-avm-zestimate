const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7860";

export interface PropertyInput {
  sqft_living: number;
  beds: number;
  baths_full: number;
  baths_half?: number;
  year_built: number;
  zip_code: string;
  lat: number;
  lng: number;
  lot_sqft?: number;
  garage_spaces?: number;
  has_pool?: number;
  assessed_value?: number;
}

export interface ShapFeature {
  feature: string;
  feature_value: number;
  shap_value: number;
  direction: "increases" | "decreases";
}

export interface PredictionResponse {
  predicted_price: number;
  lower_bound: number;
  upper_bound: number;
  confidence_score: number;
  shap_top5: ShapFeature[];
  model_version: string;
}

export interface CompProperty {
  address?: string;
  sale_price: number;
  sale_date?: string;
  sqft_living: number;
  beds?: number;
  bath_total?: number;
  distance_miles?: number;
  similarity_score: number;
}

export interface ZipRow {
  zip_code: string;
  medape: number;
  n_sales: number;
  mae: number;
}

export interface BenchmarkResponse {
  model_version: string;
  test_medape: number | null;
  test_mae: number | null;
  test_rmse: number | null;
  test_within_5pct: number | null;
  test_within_10pct: number | null;
  n_test: number | null;
  baseline_zip_median_medape: number | null;
  baseline_ppsf_medape: number | null;
  zillow_published_medape_reference: number;
  by_zip: Array<{ zip_code: string; medape: number; n_sales: number; mae: number }>;
}

export interface PropertyScanResult {
  index: number;
  list_price: number;
  predicted_price: number;
  value_gap_pct: number;
  is_undervalued: boolean;
  shap_top_driver: string | null;
}

export async function predict(input: PropertyInput): Promise<PredictionResponse> {
  const res = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getComps(
  lat: number, lng: number, sqft: number,
  beds: number, bathTotal: number, yearBuilt: number
): Promise<CompProperty[]> {
  const params = new URLSearchParams({
    lat: String(lat), lng: String(lng), sqft: String(sqft),
    beds: String(beds), bath_total: String(bathTotal), year_built: String(yearBuilt),
  });
  const res = await fetch(`${API_BASE}/comps?${params}`);
  if (!res.ok) return [];
  return res.json();
}

export async function getBenchmark(): Promise<BenchmarkResponse> {
  const res = await fetch(`${API_BASE}/benchmark`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function scanProperties(
  properties: Array<PropertyInput & { list_price: number }>
): Promise<PropertyScanResult[]> {
  const res = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ properties }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface ExplainRequest {
  predicted_price: number;
  lower_bound: number;
  upper_bound: number;
  confidence_score: number;
  shap_top5: ShapFeature[];
  zip_code: string;
  sqft_living: number;
  beds: number;
  baths_full: number;
  year_built: number;
  neighborhood_context?: string;
}

export async function explainPrediction(req: ExplainRequest): Promise<string> {
  const res = await fetch(`${API_BASE}/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  return data.explanation as string;
}

export interface SearchResult {
  id: string;
  address?: string;
  zip_code?: string;
  sqft_living?: number;
  beds?: number;
  baths_full?: number;
  year_built?: number;
  predicted_price: number;
  list_price?: number;
  value_gap_pct?: number;
  confidence_score: number;
  shap_top_driver?: string;
  created_at?: string;
}

export interface SearchResponse {
  results: SearchResult[];
  query_parsed: Record<string, unknown>;
  total: number;
}

export async function searchProperties(query: string): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface DealItem {
  id: string;
  address?: string;
  zip_code?: string;
  list_price?: number;
  predicted_price: number;
  value_gap_pct: number;
  confidence_score: number;
  beds?: number;
  baths_full?: number;
  sqft_living?: number;
  year_built?: number;
  photo_url?: string;
  condition_note?: string;
  shap_top_driver?: string;
  deal_score?: number;
  created_at?: string;
}

export async function getDeals(params?: {
  zip_code?: string;
  min_gap?: number;
}): Promise<DealItem[]> {
  const qs = new URLSearchParams();
  if (params?.zip_code) qs.set("zip_code", params.zip_code);
  if (params?.min_gap) qs.set("min_gap", String(params.min_gap));
  const res = await fetch(`${API_BASE}/deals?${qs}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
