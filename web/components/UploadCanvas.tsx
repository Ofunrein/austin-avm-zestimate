"use client";
import { useState } from "react";
import Papa from "papaparse";
import { scanProperties, PropertyInput, PropertyScanResult } from "@/lib/api";

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

export function UploadCanvas() {
  const [results, setResults] = useState<PropertyScanResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setLoading(true);
    setError(null);
    Papa.parse<Record<string, unknown>>(file, {
      header: true,
      dynamicTyping: true,
      complete: async (parsed) => {
        try {
          const properties = (parsed.data as Record<string, unknown>[]).filter(
            (r) => r.sqft_living && r.list_price
          ) as unknown as Array<PropertyInput & { list_price: number }>;
          if (properties.length === 0) {
            setError("No valid rows found. CSV needs sqft_living and list_price columns.");
            setLoading(false);
            return;
          }
          const scan = await scanProperties(properties);
          setResults(scan);
        } catch {
          setError("Scan failed — check API connection.");
        } finally {
          setLoading(false);
        }
      },
    });
  };

  return (
    <div style={{ padding: "20px 20px 24px" }}>
      <div className="panel-head" style={{ margin: "-20px -20px 20px", padding: "12px 20px" }}>
        <div className="panel-dot" />
        <span className="panel-label">UPLOAD LISTINGS CSV</span>
        <span className="panel-meta" style={{ marginLeft: "auto" }}>
          REQUIRED: sqft_living, beds, baths_full, year_built, zip_code, lat (latitude), lng (longitude), list_price
        </span>
      </div>

      <label style={{ display: "block", cursor: "pointer" }}>
        <div style={{
          border: "2px dashed var(--line-2)",
          padding: "32px",
          textAlign: "center",
          background: "var(--bg-2)",
          transition: "border-color .15s",
        }}>
          <div className="t-eyebrow" style={{ marginBottom: 8 }}>
            {loading ? "PROCESSING…" : fileName ? `LOADED: ${fileName}` : "DROP CSV HERE OR CLICK TO BROWSE"}
          </div>
          <div className="t-mono" style={{ fontSize: 11, color: "var(--mute)" }}>
            Each row = one property. Scored and ranked by model estimate vs list price.
          </div>
        </div>
        <input
          type="file"
          accept=".csv"
          style={{ display: "none" }}
          onChange={handleFile}
          disabled={loading}
        />
      </label>

      {error && (
        <div className="t-mono" style={{ fontSize: 12, color: "var(--red)", marginTop: 12 }}>
          ERR · {error}
        </div>
      )}

      {results.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span className="t-eyebrow">{results.length} PROPERTIES SCORED</span>
            <span className="t-mono" style={{ fontSize: 11, color: "var(--mute)" }}>SORTED BY VALUE GAP</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="term">
              <thead>
                <tr>
                  <th>#</th>
                  <th className="num">LIST PRICE</th>
                  <th className="num">AVM ESTIMATE</th>
                  <th className="num">GAP</th>
                  <th>TOP DRIVER</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={r.index}>
                    <td className="t-mono">{i + 1}</td>
                    <td className="t-mono num">{fmt(r.list_price)}</td>
                    <td className="t-mono num" style={{ color: "var(--gold)" }}>{fmt(r.predicted_price)}</td>
                    <td className="t-mono num" style={{ color: r.value_gap_pct > 0 ? "var(--teal)" : "var(--red)", fontWeight: 700 }}>
                      {r.value_gap_pct > 0 ? "+" : ""}{r.value_gap_pct.toFixed(1)}%
                    </td>
                    <td className="t-mono" style={{ color: "var(--mute)" }}>{r.shap_top_driver || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
