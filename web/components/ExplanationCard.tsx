"use client";
import { useEffect, useState } from "react";
import { PredictionResponse, ExplainRequest, explainPrediction } from "@/lib/api";

interface Props {
  prediction: PredictionResponse;
  zipCode: string;
  sqft: number;
  beds: number;
  baths: number;
  yearBuilt: number;
}

export function ExplanationCard({ prediction, zipCode, sqft, beds, baths, yearBuilt }: Props) {
  const [explanation, setExplanation] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setExplanation(null);
    const req: ExplainRequest = {
      predicted_price: prediction.predicted_price,
      lower_bound: prediction.lower_bound,
      upper_bound: prediction.upper_bound,
      confidence_score: prediction.confidence_score,
      shap_top5: prediction.shap_top5,
      zip_code: zipCode,
      sqft_living: sqft,
      beds,
      baths_full: baths,
      year_built: yearBuilt,
    };
    explainPrediction(req)
      .then(setExplanation)
      .catch(() => setExplanation(null))
      .finally(() => setLoading(false));
  }, [prediction.predicted_price, prediction.lower_bound, prediction.upper_bound, prediction.confidence_score, zipCode, sqft, beds, baths, yearBuilt]);

  if (!loading && !explanation) return null;

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">✦</span>
        <span className="text-sm font-semibold text-emerald-600">AI Analysis</span>
      </div>
      {loading ? (
        <div className="space-y-2">
          <div className="h-4 bg-zinc-100 rounded animate-pulse w-full" />
          <div className="h-4 bg-zinc-100 rounded animate-pulse w-5/6" />
          <div className="h-4 bg-zinc-100 rounded animate-pulse w-4/6" />
        </div>
      ) : (
        <p className="text-sm text-zinc-700 leading-relaxed">{explanation}</p>
      )}
    </div>
  );
}
