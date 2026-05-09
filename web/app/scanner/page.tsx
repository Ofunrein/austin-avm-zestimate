"use client";
import { useState } from "react";
import Papa from "papaparse";
import { scanProperties, PropertyInput, PropertyScanResult } from "@/lib/api";

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

export default function ScannerPage() {
  const [results, setResults] = useState<PropertyScanResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);

    Papa.parse<Record<string, unknown>>(file, {
      header: true,
      dynamicTyping: true,
      complete: async (parsed) => {
        try {
          const properties = ((parsed.data as Record<string, unknown>[]).filter(
            (r) => r.sqft_living && r.list_price
          ) as unknown) as Array<PropertyInput & { list_price: number }>;
          const scan = await scanProperties(properties);
          setResults(scan);
        } catch (err: unknown) {
          setError(err instanceof Error ? err.message : "Scan failed");
        } finally {
          setLoading(false);
        }
      },
    });
  };

  const downloadCsv = () => {
    const csv = Papa.unparse(results);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "undervalued_properties.csv";
    a.click();
  };

  const undervalued = results.filter((r) => r.is_undervalued);

  return (
    <main style={{ minHeight: "100vh", background: "var(--bg)", padding: "32px 28px 64px" }}>
      <div className="page-container">
        <div style={{ marginBottom: 28 }}>
          <div className="t-eyebrow" style={{ marginBottom: 8 }}>SECTION 04 · BATCH SCANNER · UNDERVALUED DETECTION</div>
          <h1 className="t-display" style={{ fontSize: 36, margin: "0 0 4px", color: "var(--ink)" }}>
            Batch <span style={{ color: "var(--gold)" }}>Scanner</span>
          </h1>
          <div className="t-mono" style={{ fontSize: 12, color: "var(--mute)" }}>
            UPLOAD CSV · PREDICT ALL · FLAG UNDERVALUED PROPERTIES
          </div>
        </div>

        {/* Upload panel */}
        <div className="panel tick-corners scanlines" style={{ marginBottom: 18 }}>
          <div className="panel-head">
            <div className="panel-dot" />
            <span className="panel-label">CSV · UPLOAD</span>
            <span className="panel-meta">REQUIRED COLS: sqft_living, beds, baths_full, year_built, zip_code, lat, lng, list_price</span>
          </div>
          <div style={{ padding: "20px 20px 24px" }}>
            <label style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 12,
              padding: "40px 20px",
              border: "1px dashed var(--line-2)",
              cursor: "pointer",
              background: "var(--bg-2)",
            }}>
              <span className="t-mono" style={{ fontSize: 28, color: "var(--mute)" }}>↑</span>
              <span className="t-eyebrow">CLICK TO SELECT CSV FILE</span>
              <input
                type="file"
                accept=".csv"
                onChange={handleFile}
                disabled={loading}
                style={{ display: "none" }}
              />
            </label>
            {loading && (
              <div style={{ marginTop: 16, textAlign: "center" }}>
                <span className="t-mono" style={{ fontSize: 12, color: "var(--gold)" }}>SCANNING… PREDICTING ALL PROPERTIES</span>
              </div>
            )}
            {error && (
              <p className="t-mono" style={{ marginTop: 12, fontSize: 11, color: "var(--red)" }}>ERR · {error}</p>
            )}
          </div>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <>
            <div style={{ display: "flex", gap: 24, marginBottom: 18 }}>
              <div className="panel" style={{ flex: 1, padding: "14px 16px", textAlign: "center" }}>
                <div className="t-eyebrow" style={{ marginBottom: 4 }}>TOTAL SCANNED</div>
                <div className="t-mono" style={{ fontSize: 22, color: "var(--ink)" }}>{results.length}</div>
              </div>
              <div className="panel" style={{ flex: 1, padding: "14px 16px", textAlign: "center", border: "1px solid var(--gold)" }}>
                <div className="t-eyebrow" style={{ marginBottom: 4 }}>UNDERVALUED</div>
                <div className="t-mono" style={{ fontSize: 22, color: "var(--gold)" }}>{undervalued.length}</div>
              </div>
              <div className="panel" style={{ flex: 1, padding: "14px 16px", textAlign: "center" }}>
                <div className="t-eyebrow" style={{ marginBottom: 4 }}>AVG GAP</div>
                <div className="t-mono" style={{ fontSize: 22, color: "var(--ink-2)" }}>
                  {undervalued.length > 0
                    ? `${(undervalued.reduce((s, r) => s + r.value_gap_pct, 0) / undervalued.length).toFixed(1)}%`
                    : "—"}
                </div>
              </div>
            </div>

            <div className="panel tick-corners">
              <div className="panel-head">
                <div className="panel-dot" />
                <span className="panel-label">SCAN RESULTS</span>
                <span className="panel-meta">{results.length} PROPERTIES · {undervalued.length} FLAGGED</span>
                <button
                  onClick={downloadCsv}
                  className="btn-ghost"
                  style={{ marginLeft: 12, padding: "4px 10px", fontSize: 10 }}
                >
                  ↓ CSV
                </button>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table className="term">
                  <thead>
                    <tr>
                      <th>IDX</th>
                      <th className="num">LIST PRICE</th>
                      <th className="num">AVM ESTIMATE</th>
                      <th className="num">GAP %</th>
                      <th className="num">STATUS</th>
                      <th>TOP DRIVER</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r) => (
                      <tr key={r.index}>
                        <td style={{ color: "var(--mute)" }}>{String(r.index).padStart(3, "0")}</td>
                        <td className="num">{fmt(r.list_price)}</td>
                        <td className="num" style={{ color: "var(--gold)" }}>{fmt(r.predicted_price)}</td>
                        <td className="num" style={{ color: r.is_undervalued ? "var(--gold)" : "var(--ink-2)" }}>
                          {r.value_gap_pct > 0 ? "+" : ""}{r.value_gap_pct.toFixed(1)}%
                        </td>
                        <td className="num">
                          {r.is_undervalued ? (
                            <span style={{
                              fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 600,
                              color: "#1a1408", background: "var(--gold)",
                              padding: "2px 8px", letterSpacing: "0.08em"
                            }}>UNDERVALUED</span>
                          ) : (
                            <span className="t-eyebrow" style={{ color: "var(--mute)" }}>FAIR</span>
                          )}
                        </td>
                        <td className="t-mono" style={{ fontSize: 11, color: "var(--mute)" }}>
                          {r.shap_top_driver ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
