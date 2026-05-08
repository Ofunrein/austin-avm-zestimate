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

  return (
    <main className="min-h-screen bg-zinc-50">
      <div className="max-w-5xl mx-auto px-4 py-12 space-y-8">
        <div>
          <a href="/" className="text-sm text-emerald-600 hover:underline">← Back</a>
          <h1 className="text-3xl font-bold text-zinc-900 mt-2">Undervalued Property Scanner</h1>
          <p className="text-zinc-500 mt-1">Upload a CSV of listings to detect properties priced below model estimate</p>
        </div>

        <div className="bg-white rounded-2xl border border-zinc-200 p-6 shadow-sm">
          <p className="text-sm text-zinc-600 mb-3">
            CSV must include:{" "}
            <code className="bg-zinc-100 px-1 rounded text-xs">
              sqft_living, beds, baths_full, year_built, zip_code, lat, lng, list_price
            </code>
          </p>
          <input
            type="file"
            accept=".csv"
            onChange={handleFile}
            className="block w-full text-sm text-zinc-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-medium file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100"
          />
          {loading && <p className="mt-3 text-sm text-zinc-500">Scanning…</p>}
          {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
        </div>

        {results.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-zinc-600">
                {results.filter((r) => r.is_undervalued).length} undervalued of {results.length} scanned
              </p>
              <button onClick={downloadCsv} className="text-sm text-emerald-600 hover:underline">
                Download CSV
              </button>
            </div>
            <div className="rounded-2xl border border-zinc-200 bg-white shadow-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-zinc-50 text-zinc-500 uppercase text-xs">
                  <tr>
                    <th className="px-4 py-3 text-left">#</th>
                    <th className="px-4 py-3 text-right">List Price</th>
                    <th className="px-4 py-3 text-right">AVM Estimate</th>
                    <th className="px-4 py-3 text-right">Gap</th>
                    <th className="px-4 py-3 text-left">Top Driver</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {results.map((r, i) => (
                    <tr key={i} className={r.is_undervalued ? "bg-emerald-50/40" : ""}>
                      <td className="px-4 py-3 text-zinc-500">{r.index + 1}</td>
                      <td className="px-4 py-3 text-right">{fmt(r.list_price)}</td>
                      <td className="px-4 py-3 text-right font-medium">{fmt(r.predicted_price)}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`font-medium ${r.value_gap_pct > 0 ? "text-emerald-600" : "text-red-500"}`}>
                          {r.value_gap_pct > 0 ? "+" : ""}{r.value_gap_pct.toFixed(1)}%
                        </span>
                        {r.is_undervalued && (
                          <span className="ml-2 text-xs bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full">
                            undervalued
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-zinc-500 text-xs">{r.shap_top_driver ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
