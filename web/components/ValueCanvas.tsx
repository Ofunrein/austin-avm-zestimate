"use client";
import { useState } from "react";
import { predict, getComps, PredictionResponse, CompProperty } from "@/lib/api";
import { PredictionCard } from "@/components/PredictionCard";
import { ShapWaterfall } from "@/components/ShapWaterfall";
import { CompsTable } from "@/components/CompsTable";
import { ExplanationCard } from "@/components/ExplanationCard";

const DEFAULT_DETAILS = {
  sqft_living: 1800, beds: 3, baths_full: 2, baths_half: 0,
  year_built: 2005, lot_sqft: 5000, garage_spaces: 1, has_pool: 0, assessed_value: 0,
};

type GeoResult = { lat: number; lng: number; zip_code: string; display: string };

async function geocodeAddress(address: string): Promise<GeoResult | null> {
  const query = address.includes("Austin") || address.includes("TX")
    ? address
    : `${address}, Austin, TX`;
  const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&addressdetails=1&limit=1&countrycodes=us`;
  try {
    const res = await fetch(url, { headers: { "User-Agent": "AustinAVM/1.0" } });
    const data = await res.json();
    if (!data.length) return null;
    const r = data[0];
    const zip = r.address?.postcode?.slice(0, 5) ?? "";
    const lat = parseFloat(r.lat);
    const lng = parseFloat(r.lon);
    // Rough Austin bounds check
    if (lat < 29.0 || lat > 31.5 || lng < -99.0 || lng > -96.5) return null;
    return { lat, lng, zip_code: zip, display: r.display_name };
  } catch {
    return null;
  }
}

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

  const handleLookup = async () => {
    if (!address.trim()) return;
    setGeoLoading(true);
    setGeoError(null);
    setGeo(null);
    setResult(null);
    const found = await geocodeAddress(address);
    setGeoLoading(false);
    if (!found) {
      setGeoError("Address not found in Austin TX. Try a full street address e.g. '1234 E 6th St, Austin, TX'");
      return;
    }
    setGeo(found);
    if (found.zip_code) setDetails(d => ({ ...d }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!geo) return;
    setLoading(true);
    setError(null);
    const form = {
      ...details,
      zip_code: geo.zip_code || "78701",
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

        {/* ── Step 1: Address lookup ── */}
        <div style={{ marginBottom: 20 }}>
          <div className="term-label" style={{ marginBottom: 8 }}>AUSTIN TX ADDRESS</div>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              className="term-input"
              type="text"
              placeholder="1234 E 6th St, Austin, TX"
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
            <div className="t-mono" style={{ fontSize: 11, color: "var(--red)", marginTop: 6 }}>
              ⚠ {geoError}
            </div>
          )}
          {geo && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
              <span style={{ width: 8, height: 8, background: "var(--teal)", borderRadius: "50%", flexShrink: 0 }} />
              <span className="t-mono" style={{ fontSize: 11, color: "var(--teal)", fontWeight: 600 }}>
                LOCATED · ZIP {geo.zip_code || "—"} · {geo.lat.toFixed(4)}, {geo.lng.toFixed(4)}
              </span>
              <button
                type="button"
                onClick={() => { setGeo(null); setAddress(""); setResult(null); }}
                className="btn-ghost"
                style={{ fontSize: 10, padding: "3px 8px", marginLeft: "auto" }}
              >
                CLEAR
              </button>
            </div>
          )}
        </div>

        {/* ── Step 2: Property details (shows after geocode) ── */}
        {geo && (
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <div className="t-eyebrow" style={{ marginBottom: 12 }}>PROPERTY DETAILS</div>
              <div className="form-grid">
                {([
                  ["sqft_living", "LIVING SQFT", "number"],
                  ["beds",        "BEDS",         "number"],
                  ["baths_full",  "FULL BATHS",   "number"],
                  ["year_built",  "YEAR BUILT",   "number"],
                ] as Array<[keyof typeof DEFAULT_DETAILS, string, string]>).map(([key, label, type]) => (
                  <div key={key}>
                    <div className="term-label">{label}</div>
                    <input
                      className="term-input"
                      type={type}
                      step="any"
                      value={details[key]}
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

            {/* Advanced override */}
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
                    ["lot_sqft",     "LOT SQFT",     "number"],
                    ["garage_spaces","GARAGE SPACES", "number"],
                    ["has_pool",     "HAS POOL (0/1)","number"],
                  ] as Array<[keyof typeof DEFAULT_DETAILS, string, string]>).map(([key, label, type]) => (
                    <div key={key}>
                      <div className="term-label">{label}</div>
                      <input
                        className="term-input"
                        type={type}
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

        {/* If no geocode yet — hint */}
        {!geo && !geoError && (
          <div className="t-mono" style={{ fontSize: 12, color: "var(--mute)", marginTop: 4 }}>
            Enter an Austin TX address above, then confirm property details to get an estimate.
          </div>
        )}

        {error && (
          <div className="t-mono" style={{ fontSize: 12, color: "var(--red)", marginTop: 12 }}>
            ERR · {error.toUpperCase()}
          </div>
        )}

        {result && geo && (
          <div style={{ marginTop: 24 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 18 }}>
              <PredictionCard result={result} />
              <ExplanationCard
                prediction={result}
                zipCode={geo.zip_code || "78701"}
                sqft={details.sqft_living}
                beds={details.beds}
                baths={details.baths_full}
                yearBuilt={details.year_built}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <ShapWaterfall features={result.shap_top5} />
            </div>
            {comps.length > 0 && <CompsTable comps={comps} />}
          </div>
        )}
      </div>
    </div>
  );
}
