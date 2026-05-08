"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { predict, getComps, PredictionResponse, CompProperty } from "@/lib/api";
import { PredictionCard } from "@/components/PredictionCard";
import { ShapWaterfall } from "@/components/ShapWaterfall";
import { CompsTable } from "@/components/CompsTable";
import { RecentValuations } from "@/components/RecentValuations";

const DEFAULT = {
  sqft_living: 1800, beds: 3, baths_full: 2, baths_half: 0,
  year_built: 2005, zip_code: "78701", lat: 30.27, lng: -97.74,
  lot_sqft: 5000, garage_spaces: 1, has_pool: 0, assessed_value: 0,
};

const FIELDS: Array<{ key: keyof typeof DEFAULT; label: string; type?: string }> = [
  { key: "sqft_living", label: "Living area (sqft)" },
  { key: "beds", label: "Bedrooms" },
  { key: "baths_full", label: "Full baths" },
  { key: "year_built", label: "Year built" },
  { key: "zip_code", label: "ZIP code", type: "text" },
  { key: "lot_sqft", label: "Lot sqft" },
  { key: "lat", label: "Latitude" },
  { key: "lng", label: "Longitude" },
];

export default function HomePage() {
  const [form, setForm] = useState(DEFAULT);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [comps, setComps] = useState<CompProperty[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-5 py-10">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
          Property Valuation
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Enter property details to get an AVM estimate with confidence interval and SHAP explanations.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
        {/* Form panel */}
        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit} className="rounded-xl border p-5 space-y-4" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            <p className="text-xs font-medium uppercase tracking-widest" style={{ color: "var(--text-subtle)" }}>Property details</p>
            <div className="grid grid-cols-2 gap-3">
              {FIELDS.map(({ key, label, type = "number" }) => (
                <div key={key}>
                  <label className="block text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>{label}</label>
                  <input
                    type={type}
                    value={form[key]}
                    onChange={(e) => setForm(f => ({ ...f, [key]: type === "number" ? Number(e.target.value) : e.target.value }))}
                    className="w-full rounded-lg px-3 py-2 text-sm outline-none transition-all"
                    style={{
                      background: "var(--surface-raised)",
                      border: "1px solid var(--border-strong)",
                      color: "var(--text-primary)",
                    }}
                    onFocus={e => { e.target.style.borderColor = "var(--accent)"; e.target.style.boxShadow = "0 0 0 2px rgba(16,185,129,0.15)"; }}
                    onBlur={e => { e.target.style.borderColor = "var(--border-strong)"; e.target.style.boxShadow = "none"; }}
                  />
                </div>
              ))}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg py-2.5 text-sm font-semibold transition-all disabled:opacity-40"
              style={{ background: "var(--accent)", color: "#000" }}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-3.5 h-3.5 rounded-full border-2 border-black/30 border-t-black animate-spin" />
                  Estimating…
                </span>
              ) : "Get Estimate"}
            </button>

            {error && (
              <p className="text-xs px-3 py-2 rounded-lg" style={{ background: "rgba(239,68,68,0.08)", color: "var(--red)", border: "1px solid rgba(239,68,68,0.15)" }}>
                {error}
              </p>
            )}
          </form>
        </div>

        {/* Results panel */}
        <div className="lg:col-span-3 space-y-4">
          <AnimatePresence mode="wait">
            {result ? (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                className="space-y-4"
              >
                <PredictionCard result={result} />
                <ShapWaterfall features={result.shap_top5} />
                {comps.length > 0 && <CompsTable comps={comps} />}
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-xl border h-64 flex flex-col items-center justify-center gap-3"
                style={{ background: "var(--surface)", borderColor: "var(--border)", borderStyle: "dashed" }}
              >
                <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: "var(--surface-raised)" }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: "var(--text-subtle)" }}>
                    <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <p className="text-sm" style={{ color: "var(--text-subtle)" }}>Enter property details to see estimate</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
      <RecentValuations />
    </div>
  );
}
