"use client";
import { SearchResult } from "@/lib/api";

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

interface Props {
  results: SearchResult[];
  total: number;
  query: string;
  onClear: () => void;
}

export function SearchResults({ results, total, query, onClear }: Props) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-zinc-500">
          <span className="font-medium text-zinc-800">{total} results</span> for &ldquo;{query}&rdquo;
        </p>
        <button
          onClick={onClear}
          className="text-xs text-emerald-600 hover:underline"
        >
          ← Value a specific property
        </button>
      </div>

      {results.length === 0 ? (
        <p className="text-zinc-400 text-sm py-8 text-center">
          No matching properties found. Try adjusting your search.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {results.map((r) => (
            <div
              key={r.id}
              className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm space-y-2"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-zinc-800 leading-tight">
                  {r.address || "Address unavailable"}
                </p>
                {r.value_gap_pct != null && r.value_gap_pct > 0 && (
                  <span className="flex-shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                    +{r.value_gap_pct.toFixed(1)}% undervalued
                  </span>
                )}
              </div>
              <p className="text-xl font-bold text-zinc-900">
                {fmt(r.predicted_price)}
              </p>
              <div className="flex flex-wrap gap-3 text-xs text-zinc-500">
                {r.zip_code && <span>ZIP {r.zip_code}</span>}
                {r.beds != null && <span>{r.beds} BD</span>}
                {r.baths_full != null && <span>{r.baths_full} BA</span>}
                {r.sqft_living != null && <span>{r.sqft_living.toLocaleString()} sqft</span>}
                {r.year_built && <span>Built {r.year_built}</span>}
              </div>
              <div className="flex items-center justify-between">
                <div className="flex-1 h-1.5 bg-zinc-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full"
                    style={{ width: `${r.confidence_score}%` }}
                  />
                </div>
                <span className="ml-2 text-xs text-zinc-400">
                  {r.confidence_score}% conf
                </span>
              </div>
              {r.shap_top_driver && (
                <p className="text-xs text-zinc-400">
                  Top driver: <span className="text-zinc-600">{r.shap_top_driver}</span>
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
