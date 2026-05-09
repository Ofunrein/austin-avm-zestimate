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

const FIELDS: Array<[keyof typeof DEFAULT, string, string, string?]> = [
  ["sqft_living",    "01 · LIVING SQFT",   "number"],
  ["lot_sqft",       "02 · LOT SQFT",       "number"],
  ["beds",           "03 · BEDS",           "number"],
  ["baths_full",     "04 · FULL BATHS",     "number"],
  ["year_built",     "05 · YEAR BUILT",     "number"],
  ["zip_code",       "06 · ZIP CODE",       "text"],
  ["lat",            "07 · LAT",            "number"],
  ["lng",            "08 · LNG",            "number"],
];

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

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', padding: '0 0 64px' }}>
      <div className="page-container">
        {/* Page heading */}
        <div className="page-heading-row">
          <div>
            <div className="t-eyebrow" style={{ marginBottom: 8 }}>SECTION 01 · HYPERLOCAL VALUATION ENGINE · AUSTIN TX</div>
            <h1 className="t-display" style={{ fontSize: 40, margin: 0, color: 'var(--ink)', lineHeight: 0.95 }}>
              Tell us what to{' '}
              <span style={{ color: 'var(--gold)', fontStyle: 'italic' }}>price.</span>
            </h1>
          </div>
          <div className="page-heading-stats">
            <div style={{ textAlign: 'right' }}>
              <div className="t-eyebrow">MEDAPE</div>
              <div className="t-mono" style={{ fontSize: 20, color: 'var(--gold)' }}>12.67%</div>
            </div>
            <div style={{ width: 1, height: 32, background: 'var(--line-2)' }} />
            <div style={{ textAlign: 'right' }}>
              <div className="t-eyebrow">WITHIN 10%</div>
              <div className="t-mono" style={{ fontSize: 20, color: 'var(--ink)' }}>45.2%</div>
            </div>
            <div style={{ width: 1, height: 32, background: 'var(--line-2)' }} />
            <div style={{ textAlign: 'right' }}>
              <div className="t-eyebrow">TEST SET</div>
              <div className="t-mono" style={{ fontSize: 20, color: 'var(--ink)' }}>15,171</div>
            </div>
          </div>
        </div>

        {/* NL Search */}
        <SearchBar onSearch={handleSearch} loading={searchLoading} />

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '16px 0' }}>
          <div style={{ flex: 1, height: 1, background: 'linear-gradient(to right, var(--line-2), transparent)' }} />
          <span className="t-eyebrow">OR INPUT SUBJECT PROPERTY</span>
          <div style={{ flex: 1, height: 1, background: 'linear-gradient(to left, var(--line-2), transparent)' }} />
        </div>

        {searchQuery ? (
          <SearchResults results={searchResults} total={searchTotal} query={searchQuery} onClear={clearSearch} />
        ) : (
          <>
            {/* Two-column: form + result */}
            <div className={result ? "grid-form-result" : ""} style={{ marginBottom: 18 }}>
              {/* Form */}
              <div className="panel tick-corners scanlines">
                <div className="panel-head">
                  <div className="panel-dot" />
                  <span className="panel-label">SUBJECT · INPUT</span>
                  <span className="panel-meta">8 FIELDS · &lt;200ms</span>
                </div>
                <form onSubmit={handleSubmit} style={{ padding: '16px 16px 20px' }}>
                  <div className="form-grid">
                    {FIELDS.map(([key, label, type]) => (
                      <div key={key}>
                        <div className="term-label">{label}</div>
                        <input
                          type={type ?? "number"}
                          value={form[key]}
                          onChange={(e) => setForm((f) => ({
                            ...f,
                            [key]: type === "text" ? e.target.value : Number(e.target.value)
                          }))}
                          className="term-input"
                        />
                      </div>
                    ))}
                  </div>
                  <div className="hr-dot" style={{ margin: '14px 0' }} />
                  <button type="submit" disabled={loading} className="btn-gold">
                    {loading ? "ESTIMATING…" : "EXECUTE VALUATION ↵"}
                  </button>
                  {error && (
                    <p className="t-mono" style={{ marginTop: 8, fontSize: 11, color: 'var(--red)' }}>
                      ERR · {error}
                    </p>
                  )}
                </form>
              </div>

              {/* Result */}
              {result && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                  <PredictionCard result={result} />
                </div>
              )}
            </div>

            {/* SHAP + AI row */}
            {result && (
              <div className="grid-shap-ai">
                <ShapWaterfall features={result.shap_top5} />
                <ExplanationCard
                  prediction={result}
                  zipCode={form.zip_code}
                  sqft={form.sqft_living}
                  beds={form.beds}
                  baths={form.baths_full}
                  yearBuilt={form.year_built}
                />
              </div>
            )}

            {/* Comps */}
            {result && comps.length > 0 && <CompsTable comps={comps} />}
          </>
        )}
      </div>
    </main>
  );
}
