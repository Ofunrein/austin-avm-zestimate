"use client";
import { useState } from "react";
import { predict, getComps, PredictionResponse, CompProperty, searchProperties, SearchResult } from "@/lib/api";
import { PredictionCard } from "@/components/PredictionCard";
import { ShapWaterfall } from "@/components/ShapWaterfall";
import { CompsTable } from "@/components/CompsTable";
import { ExplanationCard } from "@/components/ExplanationCard";
import { SearchBar } from "@/components/SearchBar";
import { SearchResults } from "@/components/SearchResults";

const DEFAULT = {
  sqft_living: 1800, beds: 3, baths_full: 2, baths_half: 0,
  year_built: 2005, zip_code: "78701", lat: 30.27, lng: -97.74,
  lot_sqft: 5000, garage_spaces: 1, has_pool: 0, assessed_value: 0,
};

export default function HomePage() {
  const [form, setForm] = useState(DEFAULT);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [comps, setComps] = useState<CompProperty[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchTotal, setSearchTotal] = useState(0);
  const [searchLoading, setSearchLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const [pred, compsData] = await Promise.all([
        predict(form),
        getComps(form.lat, form.lng, form.sqft_living, form.beds, form.baths_full, form.year_built),
      ]);
      setResult(pred);
      setComps(compsData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (query: string) => {
    setSearchLoading(true);
    setSearchQuery(query);
    try {
      const resp = await searchProperties(query);
      setSearchResults(resp.results);
      setSearchTotal(resp.total);
    } catch {
      setSearchResults([]);
      setSearchTotal(0);
    } finally {
      setSearchLoading(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery(null);
    setSearchResults([]);
  };

  const field = (key: keyof typeof DEFAULT, label: string, type = "number") => (
    <div key={key}>
      <label className="block text-xs text-zinc-500 mb-1">{label}</label>
      <input
        type={type}
        value={form[key]}
        onChange={(e) => setForm((f) => ({ ...f, [key]: type === "number" ? Number(e.target.value) : e.target.value }))}
        className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
      />
    </div>
  );

  return (
    <main className="min-h-screen bg-zinc-50">
      <div className="max-w-5xl mx-auto px-4 py-12">
        <div className="mb-10">
          <h1 className="text-3xl font-bold text-zinc-900">Austin AVM</h1>
          <p className="text-zinc-500 mt-1">Hyperlocal home valuation for Austin, TX · Temporal CV · SHAP explained</p>
          <nav className="flex gap-4 mt-4 text-sm">
            <a href="/benchmark" className="text-emerald-600 hover:underline">Benchmark Dashboard</a>
            <a href="/scanner" className="text-emerald-600 hover:underline">Undervalued Scanner</a>
            <a href="/model-card" className="text-emerald-600 hover:underline">Model Card</a>
          </nav>
        </div>

        <SearchBar onSearch={handleSearch} loading={searchLoading} />
        <div className="mt-3 mb-3 flex items-center gap-3">
          <div className="flex-1 h-px bg-zinc-200" />
          <span className="text-xs text-zinc-400">or value a specific property</span>
          <div className="flex-1 h-px bg-zinc-200" />
        </div>

        {searchQuery ? (
          <SearchResults
            results={searchResults}
            total={searchTotal}
            query={searchQuery}
            onClear={clearSearch}
          />
        ) : (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-zinc-200 p-6 shadow-sm mb-8">
          <h2 className="text-sm font-semibold text-zinc-700 mb-4">Property Details</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {field("sqft_living", "Living Area (sqft)")}
            {field("beds", "Bedrooms")}
            {field("baths_full", "Full Baths")}
            {field("year_built", "Year Built")}
            {field("zip_code", "ZIP Code", "text")}
            {field("lot_sqft", "Lot Sqft")}
            {field("lat", "Latitude")}
            {field("lng", "Longitude")}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="mt-6 w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-xl transition-colors"
          >
            {loading ? "Estimating…" : "Get Estimate"}
          </button>
          {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
        </form>
        )}

        {result && (
          <div className="space-y-6">
            <PredictionCard result={result} />
            <ShapWaterfall features={result.shap_top5} />
            <ExplanationCard
              prediction={result}
              zipCode={form.zip_code}
              sqft={form.sqft_living}
              beds={form.beds}
              baths={form.baths_full}
              yearBuilt={form.year_built}
            />
            <CompsTable comps={comps} />
          </div>
        )}
      </div>
    </main>
  );
}
