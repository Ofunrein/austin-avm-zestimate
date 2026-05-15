"use client";
import { useState, useEffect } from "react";
import { predict, getComps, lookupProperty, PredictionResponse, CompProperty } from "@/lib/api";
import { PredictionCard } from "@/components/PredictionCard";
import { ShapWaterfall } from "@/components/ShapWaterfall";
import { CompsTable } from "@/components/CompsTable";
import { ExplanationCard } from "@/components/ExplanationCard";
import { CopyButton } from "@/components/CopyButton";

const proxyImg = (url?: string) =>
  url ? `/api/img-proxy?url=${encodeURIComponent(url)}` : undefined;

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

const DEFAULT_DETAILS = {
  sqft_living: 0, beds: 0, baths_full: 0, baths_half: 0,
  year_built: 2000, lot_sqft: 5000, garage_spaces: 1, has_pool: 0, assessed_value: 0,
};

type GeoResult = {
  lat: number; lng: number; zip_code: string;
  sqft_living?: number; beds?: number; baths_full?: number; year_built?: number;
  image_url?: string;
  source: string;
};

export function ValueCanvas() {
  const [address, setAddress] = useState("");
  const [geo, setGeo] = useState<GeoResult | null>(null);
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);

  const [details, setDetails] = useState(DEFAULT_DETAILS);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [comps, setComps] = useState<CompProperty[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (!showModal) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") setShowModal(false); };
    window.addEventListener("keydown", handler);
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", handler); document.body.style.overflow = ""; };
  }, [showModal]);

  const handleLookup = async () => {
    if (!address.trim()) return;
    setGeoLoading(true);
    setGeoError(null);
    setGeo(null);
    setResult(null);

    try {
      const data = await lookupProperty(address);
      if (!data.lat || !data.lng) {
        setGeoError("Address not found in Austin TX. Try a full street address e.g. '1234 E 6th St, Austin, TX 78701'");
        setGeoLoading(false);
        return;
      }
      setGeo({
        lat: data.lat,
        lng: data.lng,
        zip_code: data.zip_code ?? "78701",
        sqft_living: data.sqft_living,
        beds: data.beds,
        baths_full: data.baths_full,
        year_built: data.year_built,
        image_url: data.image_url,
        source: data.source,
      });
      // Auto-fill any returned property details
      setDetails(d => ({
        ...d,
        sqft_living: data.sqft_living ?? d.sqft_living,
        beds: data.beds ?? d.beds,
        baths_full: data.baths_full ?? d.baths_full,
        year_built: data.year_built ?? d.year_built,
      }));
    } catch {
      setGeoError("Lookup failed — check connection.");
    } finally {
      setGeoLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!geo) return;
    setLoading(true);
    setError(null);
    const form = {
      ...details,
      zip_code: geo.zip_code,
      lat: geo.lat,
      lng: geo.lng,
    };
    try {
      const [pred, compsData] = await Promise.all([
        predict(form),
        getComps(form.lat, form.lng, form.sqft_living, form.beds, form.baths_full, form.year_built),
      ]);
      setResult(pred);
      setComps(compsData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="panel-head">
        <div className="panel-dot" />
        <span className="panel-label">VALUE A PROPERTY</span>
        <span className="panel-meta" style={{ marginLeft: "auto" }}>AUSTIN TX · XGB + LGB ENSEMBLE</span>
      </div>
      <div style={{ padding: "24px 24px 28px" }}>

        {/* ── Address lookup ── */}
        <div style={{ marginBottom: 20 }}>
          <div className="term-label" style={{ marginBottom: 8 }}>AUSTIN TX ADDRESS</div>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              className="term-input"
              type="text"
              placeholder="1234 E 6th St, Austin, TX 78701"
              value={address}
              onChange={e => { setAddress(e.target.value); setGeo(null); setResult(null); }}
              onKeyDown={e => e.key === "Enter" && (e.preventDefault(), handleLookup())}
              style={{ flex: 1, fontSize: 15 }}
            />
            <button
              type="button"
              className="btn-ghost"
              onClick={handleLookup}
              disabled={geoLoading || !address.trim()}
              style={{ whiteSpace: "nowrap", fontSize: 11, fontWeight: 700 }}
            >
              {geoLoading ? "LOOKING UP…" : "LOOK UP →"}
            </button>
          </div>
          {geoError && (
            <div className="t-mono" style={{ fontSize: 11, color: "var(--red)", marginTop: 6 }}>⚠ {geoError}</div>
          )}
          {geo && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
              <span style={{ width: 8, height: 8, background: "var(--teal)", borderRadius: "50%", flexShrink: 0 }} />
              <span className="t-mono" style={{ fontSize: 11, color: "var(--teal)", fontWeight: 600 }}>
                LOCATED · ZIP {geo.zip_code} · {geo.lat.toFixed(4)}, {geo.lng.toFixed(4)}
                {geo.source === "zillow" && (
                  <span style={{ color: "var(--gold)", marginLeft: 8 }}>· DETAILS FROM ZILLOW</span>
                )}
              </span>
              <button
                type="button"
                onClick={() => { setGeo(null); setAddress(""); setResult(null); setDetails(DEFAULT_DETAILS); }}
                className="btn-ghost"
                style={{ fontSize: 10, padding: "3px 8px", marginLeft: "auto" }}
              >
                CLEAR
              </button>
            </div>
          )}
        </div>

        {/* ── Property details (shows after geocode) ── */}
        {geo && (
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <div className="t-eyebrow" style={{ marginBottom: 12 }}>
                PROPERTY DETAILS
                {geo.source === "zillow" && (
                  <span className="t-mono" style={{ fontSize: 9, color: "var(--mute)", marginLeft: 8, fontWeight: 400 }}>
                    AUTO-FILLED · EDIT IF NEEDED
                  </span>
                )}
              </div>
              <div className="form-grid">
                {([
                  ["sqft_living", "LIVING SQFT", "number"],
                  ["beds",        "BEDS",         "number"],
                  ["baths_full",  "FULL BATHS",   "number"],
                  ["year_built",  "YEAR BUILT",   "number"],
                ] as Array<[keyof typeof DEFAULT_DETAILS, string, string]>).map(([key, label]) => (
                  <div key={key}>
                    <div className="term-label">{label}</div>
                    <input
                      className="term-input"
                      type="number"
                      step="any"
                      value={details[key] || ""}
                      placeholder="—"
                      onChange={e => setDetails(d => ({
                        ...d,
                        [key]: parseFloat(e.target.value) || 0,
                      }))}
                      required
                    />
                  </div>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <button
                type="button"
                onClick={() => setShowAdvanced(v => !v)}
                className="btn-ghost"
                style={{ fontSize: 10 }}
              >
                {showAdvanced ? "▾ HIDE ADVANCED" : "▸ ADVANCED (LOT, GARAGE, POOL)"}
              </button>
              {showAdvanced && (
                <div className="form-grid" style={{ marginTop: 10 }}>
                  {([
                    ["lot_sqft",      "LOT SQFT",      "number"],
                    ["garage_spaces", "GARAGE SPACES",  "number"],
                    ["has_pool",      "HAS POOL (0/1)", "number"],
                  ] as Array<[keyof typeof DEFAULT_DETAILS, string, string]>).map(([key, label]) => (
                    <div key={key}>
                      <div className="term-label">{label}</div>
                      <input
                        className="term-input"
                        type="number"
                        step="any"
                        value={details[key]}
                        onChange={e => setDetails(d => ({
                          ...d,
                          [key]: parseFloat(e.target.value) || 0,
                        }))}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button type="submit" className="btn-gold" disabled={loading} style={{ maxWidth: 320 }}>
              {loading ? "ESTIMATING…" : "ESTIMATE VALUE"}
            </button>
          </form>
        )}

        {!geo && !geoError && (
          <div className="t-mono" style={{ fontSize: 12, color: "var(--mute)", marginTop: 4 }}>
            Enter an Austin TX address above to get started. Property details auto-fill when available.
          </div>
        )}

        {error && (
          <div className="t-mono" style={{ fontSize: 12, color: "var(--red)", marginTop: 12 }}>
            ERR · {error.toUpperCase()}
          </div>
        )}

        {result && geo && (
          <div style={{ marginTop: 24 }}>
            <div
              onClick={() => setShowModal(true)}
              style={{ cursor: "pointer", position: "relative", marginBottom: 16 }}
              title="Click to expand"
            >
              <PredictionCard result={result} imageUrl={geo.image_url} address={address} />
              <div style={{
                position: "absolute", bottom: 10, right: 12,
                fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700, letterSpacing: "0.12em",
                color: "var(--mute)", opacity: 0.7,
              }}>
                CLICK TO EXPAND ↗
              </div>
            </div>
            <ExplanationCard
              prediction={result}
              zipCode={geo.zip_code}
              sqft={details.sqft_living}
              beds={details.beds}
              baths={details.baths_full}
              yearBuilt={details.year_built}
            />
            <div style={{ marginTop: 16, marginBottom: 16 }}>
              <ShapWaterfall features={result.shap_top5} predictedPrice={result.predicted_price} />
            </div>
            {comps.length > 0 && <CompsTable comps={comps} />}
          </div>
        )}
      </div>

      {/* ── Prediction lightbox ── */}
      {showModal && result && geo && (
        <div
          onClick={() => setShowModal(false)}
          style={{
            position: "fixed", inset: 0, zIndex: 200,
            background: "rgba(0,0,0,0.78)",
            backdropFilter: "blur(6px)",
            WebkitBackdropFilter: "blur(6px)",
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: "24px",
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              width: "100%", maxWidth: 720,
              background: "var(--bg-1)",
              border: "1px solid var(--line-2)",
              boxShadow: "0 32px 80px rgba(0,0,0,0.6)",
              overflowY: "auto",
              maxHeight: "calc(100vh - 48px)",
              position: "relative",
            }}
          >
            {/* Close */}
            <button
              onClick={() => setShowModal(false)}
              style={{
                position: "absolute", top: 10, right: 12, zIndex: 10,
                background: "rgba(0,0,0,0.55)", border: "1px solid rgba(255,255,255,0.1)",
                color: "#fff", fontSize: 14, fontFamily: "var(--font-mono)",
                padding: "3px 9px", cursor: "pointer", letterSpacing: "0.06em",
              }}
            >
              ✕
            </button>

            {/* Hero image */}
            {proxyImg(geo.image_url) && (
              <div style={{ position: "relative", width: "100%", background: "#000" }}>
                <img
                  src={proxyImg(geo.image_url)}
                  alt={address || "Property"}
                  referrerPolicy="no-referrer"
                  style={{ width: "100%", maxHeight: 480, objectFit: "contain", display: "block" }}
                  onError={(e) => { (e.target as HTMLImageElement).parentElement!.style.display = "none"; }}
                />
                <div style={{
                  position: "absolute", inset: 0,
                  background: "linear-gradient(to bottom, transparent 40%, rgba(0,0,0,0.65) 100%)",
                }} />
                <div style={{
                  position: "absolute", bottom: 14, left: 16, right: 52,
                  fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 700,
                  color: "#fff", letterSpacing: "0.08em",
                  textShadow: "0 1px 4px rgba(0,0,0,0.8)",
                }}>
                  {address.toUpperCase()}
                </div>
              </div>
            )}

            {/* Header */}
            <div className="panel-head" style={{ padding: "10px 16px" }}>
              <div className="panel-dot" />
              <span className="panel-label">AVM ESTIMATE · AUSTIN TX</span>
              <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
                <CopyButton text={address} />
                <span className="panel-meta">MODEL v{result.model_version} · 90% CI</span>
              </span>
            </div>

            {/* Price */}
            <div style={{ padding: "18px 16px 0", textAlign: "center" }}>
              <div className="t-mono" style={{
                fontSize: 48, color: "var(--gold)", fontWeight: 600,
                letterSpacing: "-0.02em", lineHeight: 1,
              }}>
                {fmt(result.predicted_price)}
              </div>
              <div className="t-mono" style={{ fontSize: 12, color: "var(--ink-2)", marginTop: 8, letterSpacing: "0.04em" }}>
                {fmt(result.lower_bound)} <span style={{ color: "var(--mute)" }}>→</span> {fmt(result.upper_bound)}
              </div>
            </div>

            {/* Property chips */}
            <div style={{ padding: "14px 16px 0", display: "flex", flexWrap: "wrap", gap: 12 }}>
              {geo.zip_code       && <span className="t-eyebrow">{geo.zip_code}</span>}
              {details.beds   > 0 && <span className="t-eyebrow">{details.beds} BD</span>}
              {details.baths_full > 0 && <span className="t-eyebrow">{details.baths_full} BA</span>}
              {details.sqft_living > 0 && <span className="t-eyebrow">{details.sqft_living.toLocaleString()} SF</span>}
              {details.year_built > 0 && <span className="t-eyebrow">BUILT {details.year_built}</span>}
            </div>

            {/* Confidence bar */}
            <div style={{ padding: "16px 16px 8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span className="t-eyebrow">CONFIDENCE</span>
                <span className="t-mono" style={{ fontSize: 11, color: "var(--gold)", fontWeight: 600 }}>
                  {result.confidence_score}/100
                </span>
              </div>
              <div className="conf-segments">
                {Array.from({ length: 20 }).map((_, i) => (
                  <div key={i} className={`conf-seg${i < Math.round((result.confidence_score / 100) * 20) ? " on" : ""}`} />
                ))}
              </div>
            </div>

            {/* AI Explanation */}
            <div style={{ padding: "8px 16px 20px" }}>
              <ExplanationCard
                prediction={result}
                zipCode={geo.zip_code}
                sqft={details.sqft_living}
                beds={details.beds}
                baths={details.baths_full}
                yearBuilt={details.year_built}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
