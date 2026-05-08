import { createClient, SupabaseClient } from "@supabase/supabase-js";

export interface PredictionRow {
  id: string;
  address: string | null;
  lat: number;
  lng: number;
  sqft_living: number;
  beds: number;
  baths_full: number;
  year_built: number;
  zip_code: string;
  predicted_price: number;
  lower_bound: number;
  upper_bound: number;
  confidence_score: number;
  shap_json: Array<{
    feature: string;
    feature_value: number;
    shap_value: number;
    direction: "increases" | "decreases";
  }> | null;
  created_at: string;
}

const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

export const supabase: SupabaseClient | null =
  url && key ? createClient(url, key) : null;

export async function fetchRecentPredictions(limit = 5): Promise<PredictionRow[]> {
  if (!supabase) return [];
  const { data, error } = await supabase
    .from("predictions")
    .select("id, address, zip_code, sqft_living, beds, baths_full, year_built, predicted_price, lower_bound, upper_bound, confidence_score, created_at")
    .order("created_at", { ascending: false })
    .limit(limit);
  if (error) {
    console.error("[supabase] fetchRecentPredictions:", error.message);
    return [];
  }
  return (data ?? []) as PredictionRow[];
}
